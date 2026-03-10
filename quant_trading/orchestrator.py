from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from sqlalchemy import select

from quant_trading.config import get_settings
from quant_trading.db.models import DailyMark, Fill
from quant_trading.db.queries import reconcile_trade_ledger, snapshot_from_ledger
from quant_trading.db.repository import QuantRepository
from quant_trading.jobs import scheduled_job_specs
from quant_trading.memory.reflection import run_reflection
from quant_trading.reports.weekly import write_weekly_report
from quant_trading.schemas import (
    AgentID,
    AgentResult,
    DecisionType,
    JobRunInput,
    JobStatus,
    MarketContext,
    PipelineSlot,
    PortfolioSnapshot,
    SessionState,
    TradeDecision,
    UniverseItem,
)
from quant_trading.services.backtester import BackfillSummary, BacktesterService
from quant_trading.services.execution import ExecutionResult, ExecutionService
from quant_trading.services.holiday_sync import HolidaySyncService
from quant_trading.services.market_clock import MarketClock, MarketSnapshot
from quant_trading.services.market_data import MarketDataService
from quant_trading.services.pairs import PairValidation, PairsService
from quant_trading.services.risk import compute_market_regime, compute_risk_metrics
from quant_trading.timeutils import market_today, market_now
from quant_trading.tools.cliproxy import CLIProxyGateway
from quant_trading.tools.yfinance_client import YFinanceClient


PIPELINE_SLOT_TIMES = {
    spec.job_name: time(int(spec.cron["hour"]), int(spec.cron["minute"]))
    for spec in scheduled_job_specs()
    if spec.handler_name == "run_pipeline" and spec.cron
}
PIPELINE_SLOT_ORDER = sorted(PIPELINE_SLOT_TIMES.items(), key=lambda item: item[1])
TRADABLE_PIPELINE_STATES = {SessionState.OPEN, SessionState.POST_MARKET}
PIPELINE_SETUP_SEQUENCE = (AgentID.DISCOVERY, AgentID.UNIVERSE)
PIPELINE_RESEARCH_SEQUENCE = (
    AgentID.QUALITY,
    AgentID.MACRO,
    AgentID.EVENTS,
    AgentID.SENTIMENT,
    AgentID.SECTOR,
    AgentID.OWNERSHIP,
    AgentID.RISK,
    AgentID.MOMENTUM,
    AgentID.REVERSION,
    AgentID.PAIRS,
    AgentID.LIQUIDITY,
)
PIPELINE_FINAL_SEQUENCE = (AgentID.BACKTESTER,)

# Public constant used by ops tooling/tests to build an agent registry.
PIPELINE_SEQUENCE = (*PIPELINE_SETUP_SEQUENCE, *PIPELINE_RESEARCH_SEQUENCE, *PIPELINE_FINAL_SEQUENCE)


@dataclass(slots=True)
class PipelineOutput:
    run_id: str
    agent_results: dict[str, AgentResult]
    trade_decisions: list[TradeDecision]
    executions: list[ExecutionResult]


class Orchestrator:
    def __init__(
        self,
        repository: QuantRepository,
        agents: dict[str, object],
        boss: object,
        market_data: YFinanceClient | None = None,
        gateway: CLIProxyGateway | None = None,
    ) -> None:
        self.settings = get_settings()
        self.repository = repository
        self.agents = agents
        self.boss = boss
        self.market_clock = MarketClock(self.settings)
        self.market_data_service = MarketDataService(self.settings, self.repository, client=market_data)
        self.market_data = self.market_data_service.client
        self.execution_service = ExecutionService(repository)
        self.backtester = BacktesterService(
            session_factory=self.repository.session_factory,
            market_data=self.market_data_service.client,
            conviction_threshold=self.settings.market.conviction_threshold,
        )
        self.holidays = HolidaySyncService(self.settings)
        self.pairs = PairsService(output_path=self.settings.data_dir / "validated_pairs.json", market_data=self.market_data_service.client)
        self.gateway = gateway

    def startup_recovery(self) -> None:
        now = datetime.now(UTC)
        recovered_jobs = self.repository.abort_stale_jobs(now=now)
        recovered_slots = self.repository.recover_running_trading_slots(now=now)
        recovered_requests = self.repository.recover_expired_job_requests(now=now)
        self.holidays.refresh_if_needed(now)
        self.repository.reconcile_portfolio_from_fills()
        if recovered_jobs or recovered_slots or recovered_requests:
            self.repository.log_operator_action(
                "startup.recovery",
                {
                    "aborted_jobs": recovered_jobs,
                    "aborted_slots": recovered_slots,
                    "failed_requests": recovered_requests,
                },
            )

        snapshot = self.market_clock.snapshot(now)
        missed_slots = self._missed_pipeline_slots(snapshot)
        if not missed_slots:
            return
        if not snapshot.calendar_ready:
            self.repository.log_operator_action(
                "startup.catchup_blocked",
                {"reason": "holiday_calendar_unavailable", "slots": missed_slots, "status": snapshot.holiday_status},
            )
            return
        if snapshot.session_state not in TRADABLE_PIPELINE_STATES:
            self.repository.log_operator_action(
                "startup.catchup_blocked",
                {"reason": "session_inactive", "slots": missed_slots, "session_state": snapshot.session_state.value},
            )
            return
        for slot_name in missed_slots:
            try:
                result = self.run_pipeline(trigger=f"catchup:{slot_name}")
            except Exception as exc:  # pragma: no cover - defensive path
                self.repository.log_operator_action("startup.catchup_failed", {"slot": slot_name, "error": str(exc)})
                break
            self.repository.log_operator_action("startup.catchup_ran", {"slot": slot_name, "run_id": result.run_id})

    def run_pipeline(self, trigger: str = "manual") -> PipelineOutput:
        started_at = datetime.now(UTC)
        snapshot = self.market_clock.snapshot(started_at)

        # 1. Validation & Skip Logic
        slot_name = self._resolve_pipeline_slot(trigger=trigger, snapshot=snapshot)
        skip_reason = self._pipeline_skip_reason(snapshot=snapshot)
        if skip_reason:
            return self._record_skipped_pipeline_run(trigger=trigger, snapshot=snapshot, reason=skip_reason, slot_name=slot_name)

        runtime_state = self.repository.sync_entries_blocked_from_desk_messages()
        if runtime_state.get("autonomy_paused") and not trigger.startswith("manual"):
            return self._record_skipped_pipeline_run(trigger=trigger, snapshot=snapshot, reason="autonomy_paused", slot_name=slot_name)

        # 2. Concurrency Control & Run Initialization
        run_id = str(uuid4())
        if slot_name is not None:
            if not self._claim_slot(snapshot, slot_name, trigger, run_id):
                existing = self.repository.get_trading_slot(slot_date=snapshot.date_local, slot_name=slot_name)
                return PipelineOutput(run_id=existing.run_id if existing else run_id, agent_results={}, trade_decisions=[], executions=[])

        run_id = self.repository.create_market_day_run(
            trigger=trigger,
            run_id=run_id,
            run_date=snapshot.date_local,
            payload={"slot": slot_name, "session_state": snapshot.session_state.value},
        )

        try:
            # 3. Execution
            results, context = self._execute_agent_pipeline(run_id, snapshot)
            decisions = self.boss.run(context)
            executions = self._process_decisions(run_id, context, decisions, runtime_state)

            # 4. Finalization
            self._finalize_pipeline_run(run_id, trigger, slot_name, snapshot, decisions, executions)
            return PipelineOutput(run_id=run_id, agent_results=results, trade_decisions=decisions, executions=executions)

        except Exception as exc:
            self._handle_pipeline_failure(run_id, trigger, slot_name, snapshot, exc)
            raise

    def _claim_slot(self, snapshot: MarketSnapshot, slot_name: str, trigger: str, run_id: str) -> bool:
        claimed = self.repository.claim_trading_slot(
            slot_date=snapshot.date_local,
            slot_name=slot_name,
            trigger=trigger,
            run_id=run_id,
            details={"trigger": trigger},
        )
        if not claimed:
            existing = self.repository.get_trading_slot(slot_date=snapshot.date_local, slot_name=slot_name)
            self.repository.log_operator_action(
                "pipeline.duplicate_blocked",
                {
                    "trigger": trigger,
                    "slot": slot_name,
                    "run_id": existing.run_id if existing is not None else None,
                },
            )
        return claimed

    def _build_context(self, run_id: str, snapshot: MarketSnapshot) -> MarketContext:
        return MarketContext(
            run_id=run_id,
            timestamp_utc=snapshot.timestamp_utc,
            market="NSE",
            date=snapshot.date_local,
            time_ist=snapshot.time_local,
            session_state=snapshot.session_state,
            is_market_day=snapshot.is_market_day,
            portfolio=self.repository.get_portfolio_snapshot(),
            runtime_overrides=self.repository.get_runtime_overrides(),
        )

    def _apply_result_to_context(
        self, context: MarketContext, result: AgentResult, upstream_results: dict[str, AgentResult]
    ) -> MarketContext:
        updates: dict[str, Any] = {"upstream_results": upstream_results}

        if result.agent_id == AgentID.DISCOVERY:
            if "discovery_plan" in result.artifacts:
                updates["universe_discovery"] = result.artifacts["discovery_plan"]

        if result.agent_id == AgentID.UNIVERSE:
            if "universe" in result.artifacts:
                universe = [
                    UniverseItem(**item) if isinstance(item, dict) else item
                    for item in result.artifacts["universe"]
                ]
                updates["universe"] = universe
                updates["price_bundle"] = self.market_data_service.load_price_bundle(universe)

        if result.agent_id == AgentID.RISK:
            if "market_regime" in result.artifacts:
                updates["regime"] = result.artifacts["market_regime"]

        return context.model_copy(update=updates)

    def _execute_agent_pipeline(self, run_id: str, snapshot: MarketSnapshot) -> tuple[dict[str, AgentResult], MarketContext]:
        results: dict[str, AgentResult] = {}
        context = self._build_context(run_id=run_id, snapshot=snapshot)
        disabled_agents = set(context.runtime_overrides.get("disabled_agents", []))

        # 1. Sequential setup phase
        for agent_id in PIPELINE_SETUP_SEQUENCE:
            result = self._run_single_agent(agent_id, run_id, context)
            if result:
                results[agent_id] = result
                context = self._apply_result_to_context(context=context, result=result, upstream_results=results)

        # 2. Parallel research phase
        research_agents = [agent_id for agent_id in PIPELINE_RESEARCH_SEQUENCE if agent_id not in disabled_agents]
        research_job_ids: dict[str, str] = {}
        for agent_id in research_agents:
            research_job_ids[agent_id] = self.repository.create_job_run(
                JobRunInput(
                    run_id=run_id,
                    job_name=agent_id,
                    status=JobStatus.RUNNING,
                    started_at=datetime.now(UTC),
                )
            )

        with ThreadPoolExecutor(max_workers=min(len(research_agents), 8), thread_name_prefix="agent-pool") as pool:
            futures = {pool.submit(self.agents[agent_id].run, context): agent_id for agent_id in research_agents}
            for future in as_completed(futures):
                agent_id = futures[future]
                job_id = research_job_ids[agent_id]
                try:
                    result = future.result()
                except Exception as exc:
                    self.repository.finish_job_run(
                        job_id=job_id,
                        status=JobStatus.FAILED,
                        finished_at=datetime.now(UTC),
                        details={"error": str(exc)},
                    )
                    raise
                self.repository.finish_job_run(
                    job_id=job_id,
                    status=JobStatus.SUCCEEDED,
                    finished_at=datetime.now(UTC),
                    details={"warnings": getattr(result, "warnings", []), "status": getattr(result, "status", "success")},
                )
                self.repository.record_agent_run(result=result)
                results[agent_id] = result

        # After parallel run, we need to merge all results into context sequentially for any final agents
        for agent_id in PIPELINE_RESEARCH_SEQUENCE:
            if agent_id in results:
                context = self._apply_result_to_context(context=context, result=results[agent_id], upstream_results=results)

        # 3. Final sequential phase
        for agent_id in PIPELINE_FINAL_SEQUENCE:
            result = self._run_single_agent(agent_id, run_id, context)
            if result:
                results[agent_id] = result
                context = self._apply_result_to_context(context=context, result=result, upstream_results=results)

        return results, context

    def _run_single_agent(self, agent_id: str, run_id: str, context: MarketContext) -> AgentResult | None:
        if agent_id in context.runtime_overrides.get("disabled_agents", []):
            return None

        agent = self.agents[agent_id]
        job_id = self.repository.create_job_run(
            JobRunInput(
                run_id=run_id,
                job_name=agent_id,
                status=JobStatus.RUNNING,
                started_at=datetime.now(UTC),
            )
        )
        try:
            result = agent.run(context)
            self.repository.finish_job_run(
                job_id=job_id,
                status=JobStatus.SUCCEEDED,
                finished_at=datetime.now(UTC),
                details={"warnings": result.warnings, "status": result.status},
            )
            self.repository.record_agent_run(result=result)
            return result
        except Exception as exc:
            self.repository.finish_job_run(
                job_id=job_id,
                status=JobStatus.FAILED,
                finished_at=datetime.now(UTC),
                details={"error": str(exc)},
            )
            raise

    def _process_decisions(self, run_id: str, context: MarketContext, decisions: list[TradeDecision], runtime_state: dict) -> list[ExecutionResult]:
        self.repository.record_trade_decisions(run_id=run_id, decisions=decisions)
        executions: list[ExecutionResult] = []
        for decision in decisions:
            if (runtime_state.get("entries_blocked") or runtime_state.get("exits_only")) and decision.decision is DecisionType.BUY:
                continue
            execution = self.execution_service.execute(run_id=run_id, context=context, decision=decision)
            if execution is not None:
                executions.append(execution)
        self.repository.reconcile_portfolio_from_fills()
        return executions

    def _finalize_pipeline_run(self, run_id: str, trigger: str, slot_name: str | None, snapshot: MarketSnapshot, decisions: list[TradeDecision], executions: list[ExecutionResult]) -> None:
        self.repository.finish_market_day_run(
            run_id=run_id,
            status=JobStatus.SUCCEEDED,
            finished_at=datetime.now(UTC),
            details={
                "trigger": trigger,
                "slot": slot_name,
                "decision_count": len(decisions),
                "execution_count": len(executions),
            },
        )
        if slot_name is not None:
            self.repository.finish_trading_slot(
                slot_date=snapshot.date_local,
                slot_name=slot_name,
                status=JobStatus.SUCCEEDED,
                finished_at=datetime.now(UTC),
                details={"run_id": run_id, "trigger": trigger},
            )

    def _handle_pipeline_failure(self, run_id: str, trigger: str, slot_name: str | None, snapshot: MarketSnapshot, exc: Exception) -> None:
        self.repository.finish_market_day_run(
            run_id=run_id,
            status=JobStatus.FAILED,
            finished_at=datetime.now(UTC),
            details={"trigger": trigger, "slot": slot_name, "error": str(exc)},
        )
        if slot_name is not None:
            self.repository.finish_trading_slot(
                slot_date=snapshot.date_local,
                slot_name=slot_name,
                status=JobStatus.FAILED,
                finished_at=datetime.now(UTC),
                details={"run_id": run_id, "trigger": trigger, "error": str(exc)},
            )

    def _resolve_pipeline_slot(self, *, trigger: str, snapshot: MarketSnapshot) -> str | None:
        if trigger in PIPELINE_SLOT_TIMES:
            return trigger
        if trigger == "scheduled":
            return PipelineSlot.MORNING.value
        if trigger.startswith("catchup:"):
            candidate = trigger.split(":", 1)[1]
            return candidate if candidate in PIPELINE_SLOT_TIMES else None
        if trigger in {"bootstrap", "pipeline", "manual:web", "manual"} or trigger.startswith("manual"):
            if snapshot.time_local < time.fromisoformat(self.settings.market.entry_window_open):
                return None
            due_slots = [slot for slot, slot_time in PIPELINE_SLOT_ORDER if slot_time <= snapshot.time_local]
            if due_slots:
                return due_slots[-1]
            return PIPELINE_SLOT_ORDER[0][0] if PIPELINE_SLOT_ORDER else None
        return None

    def _pipeline_skip_reason(self, *, snapshot: object) -> str | None:
        if not snapshot.calendar_ready:
            return "holiday_calendar_unavailable"
        if not snapshot.is_market_day:
            return "market_closed"
        if snapshot.session_state not in TRADABLE_PIPELINE_STATES:
            return "session_inactive"
        return None

    def _record_skipped_pipeline_run(
        self,
        *,
        trigger: str,
        snapshot: object,
        reason: str,
        slot_name: str | None,
    ) -> PipelineOutput:
        run_id = self.repository.create_market_day_run(
            trigger=f"{trigger}:skipped",
            run_date=snapshot.date_local,
            payload={
                "trigger": trigger,
                "slot": slot_name,
                "skip_reason": reason,
                "session_state": snapshot.session_state.value,
                "holiday_status": snapshot.holiday_status,
            },
        )
        self.repository.finish_market_day_run(
            run_id=run_id,
            status=JobStatus.SUCCEEDED,
            finished_at=datetime.now(UTC),
            details={"trigger": trigger, "slot": slot_name, "skipped": reason},
        )
        return PipelineOutput(run_id=run_id, agent_results={}, trade_decisions=[], executions=[])

    def _missed_pipeline_slots(self, snapshot: object) -> list[str]:
        if not snapshot.calendar_ready or not snapshot.is_market_day:
            return []
        if snapshot.time_local > time.fromisoformat(self.settings.market.exit_window_close):
            return []
        expected = [slot for slot, slot_time in PIPELINE_SLOT_ORDER if slot_time <= snapshot.time_local]
        if not expected:
            return []
        existing = {row.slot_name for row in self.repository.list_trading_slots(slot_date=snapshot.date_local)}
        return [slot for slot in expected if slot not in existing]

    def run_reflection(self, agent_ids: Iterable[str]) -> None:
        with self.repository.session_factory() as session:
            for agent_id in agent_ids:
                run_reflection(
                    session=session,
                    gateway=self.gateway if (self.gateway and self.gateway.is_configured()) else None,
                    agent_id=agent_id,
                    reflection_date=market_today(self.settings),
                    model_alias=self.settings.cliproxy.model_aliases.get("reflection", "reflection"),
                )

    def run_backfill(self, as_of: date | None = None) -> BackfillSummary:
        return self.backtester.run_backfill(as_of=as_of)

    def run_pairs_revalidation(self) -> list[PairValidation]:
        return self.pairs.revalidate()

    def live_portfolio_snapshot(self) -> PortfolioSnapshot:
        return self.market_data_service.get_live_portfolio_snapshot()

    def sync_holidays(self) -> Path:
        return self.holidays.refresh_if_needed()

    def mark_end_of_day(self) -> None:
        market_snapshot = self.market_clock.snapshot(market_now())
        positions = self.repository.list_positions()
        price_bundle = self.market_data_service.load_price_bundle([UniverseItem(ticker=position.ticker) for position in positions]) if positions else {
            self.settings.market.benchmark: self.market_data_service.client.load_price_data(self.settings.market.benchmark, period="1y"),
            "^INDIAVIX": self.market_data_service.client.load_price_data("^INDIAVIX", period="6mo"),
        }
        latest_prices: dict[str, float] = {}
        for position in positions:
            price = price_bundle.get(position.ticker)
            latest = price.last_price if price is not None else None
            if latest is None and price is not None and price.history:
                latest = price.history[-1].close
            if latest is not None:
                latest_prices[position.ticker] = latest

        benchmark = price_bundle.get(self.settings.market.benchmark)
        benchmark_close = None
        benchmark_return_pct = None
        if benchmark is not None and benchmark.history:
            benchmark_close = benchmark.last_price or benchmark.history[-1].close
            if len(benchmark.history) >= 2 and benchmark.history[-2].close > 0:
                benchmark_return_pct = ((benchmark.history[-1].close / benchmark.history[-2].close) - 1.0) * 100

        vix_price = price_bundle.get("^INDIAVIX")
        india_vix = vix_price.last_price if vix_price is not None else (vix_price.history[-1].close if vix_price and vix_price.history else None)
        regime = compute_market_regime(india_vix)

        risk_metrics = compute_risk_metrics(price_bundle=price_bundle, positions=positions, benchmark_ticker=self.settings.market.benchmark)
        previous_mark = next((row for row in self.repository.list_daily_marks(limit=30) if row.mark_date < market_snapshot.date_local), None)
        portfolio_snapshot = self.repository.mark_portfolio(
            price_map=latest_prices,
            mark_date=market_snapshot.date_local,
            benchmark_close=benchmark_close,
            benchmark_return_pct=benchmark_return_pct,
            details={
                "regime": regime,
                "india_vix": india_vix,
                **risk_metrics,
            },
        )
        total_return_pct = ((portfolio_snapshot.portfolio_value / self.settings.market.initial_capital) - 1.0) * 100
        daily_return_pct = None
        if previous_mark is not None and previous_mark.portfolio_value > 0:
            daily_return_pct = ((portfolio_snapshot.portfolio_value / previous_mark.portfolio_value) - 1.0) * 100
        alpha_pct = daily_return_pct - benchmark_return_pct if daily_return_pct is not None and benchmark_return_pct is not None else None
        self.repository.mark_portfolio(
            price_map=latest_prices,
            mark_date=market_snapshot.date_local,
            benchmark_close=benchmark_close,
            benchmark_return_pct=benchmark_return_pct,
            alpha_pct=alpha_pct,
            details={
                "regime": regime,
                "india_vix": india_vix,
                "total_return_pct": round(total_return_pct, 4),
                "daily_return_pct": round(daily_return_pct, 4) if daily_return_pct is not None else None,
                **risk_metrics,
            },
        )

    def write_weekly_report(self) -> Path:
        output_path = self.settings.reports_dir / f"week_{market_today(self.settings).isoformat()}.md"
        with self.repository.session_factory() as session:
            return write_weekly_report(session, output_path)

    def repair_portfolio_history(self) -> dict[str, int]:
        with self.repository.session_factory() as session:
            marks = list(session.scalars(select(DailyMark).order_by(DailyMark.mark_date.asc())).all())
            fills = list(session.scalars(select(Fill).order_by(Fill.created_at.asc(), Fill.id.asc())).all())
            if not marks:
                snapshot = self.repository.reconcile_portfolio_from_fills()
                return {
                    "marks_repaired": 0,
                    "open_positions": snapshot.open_positions,
                    "tickers_loaded": 0,
                }
            tickers = sorted({fill.ticker for fill in fills})
            history_cache = {ticker: self.market_data_service.get_historical_close_series(f"{ticker}.NS") for ticker in tickers}
            previous_portfolio_value: float | None = None
            for mark in marks:
                ledger = reconcile_trade_ledger(session, starting_cash=self.settings.market.initial_capital, as_of=mark.mark_date)
                price_map = {
                    position.ticker: price
                    for position in ledger.positions
                    if (price := self.market_data_service.close_on_or_before(history_cache.get(position.ticker, []), mark.mark_date)) is not None
                }
                snapshot = snapshot_from_ledger(ledger, price_map=price_map)
                daily_return_pct = None
                if previous_portfolio_value is not None and previous_portfolio_value > 0:
                    daily_return_pct = ((snapshot.portfolio_value / previous_portfolio_value) - 1.0) * 100
                details = dict(mark.details or {})
                details.update(
                    {
                        "priced_positions": snapshot.priced_positions,
                        "unpriced_positions": snapshot.unpriced_positions,
                        "total_return_pct": round(((snapshot.portfolio_value / self.settings.market.initial_capital) - 1.0) * 100, 4),
                        "daily_return_pct": round(daily_return_pct, 4) if daily_return_pct is not None else None,
                    }
                )
                mark.portfolio_value = snapshot.portfolio_value
                mark.cash_balance = snapshot.cash_balance
                mark.realized_pnl = ledger.realized_pnl_by_date.get(mark.mark_date, 0.0)
                mark.total_realized_pnl = snapshot.total_realized_pnl
                mark.unrealized_pnl = snapshot.total_unrealized_pnl
                mark.alpha_pct = (
                    daily_return_pct - mark.benchmark_return_pct
                    if daily_return_pct is not None and mark.benchmark_return_pct is not None
                    else None
                )
                mark.details = details
                previous_portfolio_value = snapshot.portfolio_value
            session.commit()
        snapshot = self.repository.reconcile_portfolio_from_fills()
        return {
            "marks_repaired": len(marks),
            "open_positions": snapshot.open_positions,
            "tickers_loaded": len(tickers),
        }

    def heartbeat(self) -> None:
        run_id = self.repository.create_market_day_run(trigger="heartbeat")
        self.repository.finish_market_day_run(run_id=run_id, status=JobStatus.SUCCEEDED, finished_at=market_now(), details={"trigger": "heartbeat"})
