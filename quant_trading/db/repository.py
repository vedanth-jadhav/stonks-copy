from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from quant_trading.config import get_settings
from quant_trading.execution import compute_delivery_charges, compute_entry_fill, compute_exit_fill
from quant_trading.memory.graph import GraphMemory
from quant_trading.memory.structured import latest_lessons
from quant_trading.schemas import AgentResult, JobRequestStatus, JobRunInput, JobStatus, PortfolioSnapshot, PriceData, ReflectionLesson, TradeDecision, UniverseItem
from quant_trading.timeutils import market_date_for, market_today

from .models import (
    AgentICHistory,
    AgentRun,
    AgentSignalOutcome,
    DailyMark,
    DeskMessage,
    Fill,
    JobRun,
    JobRequest,
    OperatorAction,
    Order,
    Position,
    Reflection,
    RuntimeOverride,
    RuntimeState,
    ServiceHeartbeat,
    SignalHistory,
    TradingSlot,
    TradeDecisionRecord,
)
from .queries import (
    PortfolioLedger,
    PositionProjection,
    latest_charge_schedule,
    mark_stale_running_jobs,
    reconcile_portfolio,
    reconcile_trade_ledger,
    snapshot_from_ledger,
)
from .session import create_engine_and_sessionmaker


def _parse_desk_message(raw_text: str) -> dict[str, object]:
    text = raw_text.strip()
    lower = text.lower()
    tokens = [token.strip(",. ") for token in text.split()]
    symbols = [token.upper().replace(".NS", "") for token in tokens]
    ticker = next((token for token in symbols if token.isalpha() and 2 <= len(token) <= 15), None)
    parsed: dict[str, object] = {"kind": "note_only", "summary": text[:160]}
    if "ban" in lower and ticker:
        parsed = {"kind": "ban_ticker", "ticker": ticker}
    elif "watch" in lower and ticker:
        parsed = {"kind": "watch_ticker", "ticker": ticker}
    elif "quality only" in lower:
        parsed = {"kind": "quality_only"}
    elif "pause entries" in lower:
        parsed = {"kind": "pause_entries"}
    elif "reduce max deploy" in lower:
        parsed = {"kind": "reduce_max_deploy"}
    elif ("disable" in lower or "turn off" in lower) and "agent_" in lower:
        agent = next((token for token in tokens if token.startswith("agent_")), None)
        if agent:
            parsed = {"kind": "disable_agent", "agent_id": agent}
    elif "rerun" in lower and "agent_" in lower:
        agent = next((token for token in tokens if token.startswith("agent_")), None)
        if agent:
            parsed = {"kind": "rerun_agent", "agent_id": agent}
    elif "bug" in lower or "investigate" in lower:
        parsed = {"kind": "investigate_bug", "summary": text[:160]}
    return parsed


class QuantRepository:
    def __init__(self, engine: object, session_factory: sessionmaker[Session] | None = None) -> None:
        self.engine = engine
        self.session_factory = session_factory
        if self.session_factory is None:
            _, self.session_factory = create_engine_and_sessionmaker(get_settings().database.url)

    def create_market_day_run(self, trigger: str, *, run_id: str | None = None, run_date: date | None = None, payload: dict | None = None) -> str:
        effective_run_id = run_id or str(uuid4())
        with self.session_factory() as session:
            session.add(
                JobRun(
                    id=effective_run_id,
                    run_date=run_date or market_today(),
                    job_name=f"market-day:{trigger}",
                    status=JobStatus.RUNNING.value,
                    started_at=datetime.now(UTC),
                    payload={"trigger": trigger, **(payload or {})},
                )
            )
            session.commit()
        return effective_run_id

    def claim_trading_slot(self, *, slot_date: date, slot_name: str, trigger: str, run_id: str, details: dict | None = None) -> bool:
        with self.session_factory() as session:
            session.add(
                TradingSlot(
                    slot_date=slot_date,
                    slot_name=slot_name,
                    trigger=trigger,
                    run_id=run_id,
                    status=JobStatus.RUNNING.value,
                    details=details or {},
                )
            )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
        return True

    def finish_trading_slot(
        self,
        *,
        slot_date: date,
        slot_name: str,
        status: JobStatus,
        finished_at: datetime,
        details: dict | None = None,
    ) -> None:
        with self.session_factory() as session:
            row = session.scalar(
                select(TradingSlot)
                .where(
                    TradingSlot.slot_date == slot_date,
                    TradingSlot.slot_name == slot_name,
                )
                .limit(1)
            )
            if row is None:
                return
            row.status = status.value
            row.finished_at = finished_at
            row.details = {**(row.details or {}), **(details or {})}
            session.commit()

    def get_trading_slot(self, *, slot_date: date, slot_name: str) -> TradingSlot | None:
        with self.session_factory() as session:
            return session.scalar(
                select(TradingSlot)
                .where(
                    TradingSlot.slot_date == slot_date,
                    TradingSlot.slot_name == slot_name,
                )
                .limit(1)
            )

    def list_trading_slots(self, *, slot_date: date | None = None, limit: int | None = None) -> list[TradingSlot]:
        with self.session_factory() as session:
            stmt = select(TradingSlot).order_by(TradingSlot.slot_date.desc(), TradingSlot.claimed_at.desc(), TradingSlot.id.desc())
            if slot_date is not None:
                stmt = stmt.where(TradingSlot.slot_date == slot_date)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def recover_running_trading_slots(self, *, now: datetime | None = None) -> int:
        effective_now = now or datetime.now(UTC)
        with self.session_factory() as session:
            rows = session.scalars(select(TradingSlot).where(TradingSlot.status == JobStatus.RUNNING.value)).all()
            for row in rows:
                row.status = JobStatus.ABORTED.value
                row.finished_at = effective_now
                row.details = {**(row.details or {}), "error": "Recovered after process restart."}
            session.commit()
            return len(rows)

    def create_job_run(self, payload: JobRunInput) -> str:
        job_id = str(uuid4())
        with self.session_factory() as session:
            session.add(
                JobRun(
                    id=job_id,
                    run_date=market_date_for(payload.started_at),
                    job_name=payload.job_name,
                    status=payload.status.value,
                    started_at=payload.started_at,
                    payload={"run_id": payload.run_id},
                )
            )
            session.commit()
        return job_id

    def finish_job_run(self, job_id: str, status: JobStatus, finished_at: datetime, details: dict) -> None:
        with self.session_factory() as session:
            job = session.get(JobRun, job_id)
            if job is None:
                return
            job.status = status.value
            job.finished_at = finished_at
            job.payload = {**(job.payload or {}), **details}
            if status is JobStatus.FAILED:
                job.error = details.get("error")
            session.commit()

    def finish_market_day_run(self, run_id: str, status: JobStatus, finished_at: datetime, details: dict | None = None) -> None:
        self.finish_job_run(job_id=run_id, status=status, finished_at=finished_at, details=details or {})

    def enqueue_job_request(
        self,
        *,
        job_name: str,
        requested_by: str,
        payload: dict | None = None,
        dedupe_key: str | None = None,
    ) -> JobRequest:
        active_statuses = {JobRequestStatus.QUEUED.value, JobRequestStatus.RUNNING.value}
        effective_dedupe_key = dedupe_key or job_name
        with self.session_factory() as session:
            existing = session.scalar(
                select(JobRequest)
                .where(
                    JobRequest.dedupe_key == effective_dedupe_key,
                    JobRequest.status.in_(active_statuses),
                )
                .order_by(JobRequest.requested_at.desc(), JobRequest.id.desc())
                .limit(1)
            )
            if existing is not None:
                return existing
            row = JobRequest(
                job_name=job_name,
                dedupe_key=effective_dedupe_key,
                requested_by=requested_by,
                status=JobRequestStatus.QUEUED.value,
                payload=payload or {},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def claim_next_job_request(self, *, lease_owner: str, lease_seconds: int = 1800) -> JobRequest | None:
        now = datetime.now(UTC)
        lease_expires_at = now.timestamp() + lease_seconds
        with self.session_factory() as session:
            candidate = session.scalar(
                select(JobRequest)
                .where(JobRequest.status == JobRequestStatus.QUEUED.value)
                .order_by(JobRequest.requested_at.asc(), JobRequest.id.asc())
                .limit(1)
            )
            if candidate is None:
                return None
            claimed = session.execute(
                update(JobRequest)
                .where(
                    JobRequest.id == candidate.id,
                    JobRequest.status == JobRequestStatus.QUEUED.value,
                )
                .values(
                    status=JobRequestStatus.RUNNING.value,
                    lease_owner=lease_owner,
                    lease_expires_at=datetime.fromtimestamp(lease_expires_at, UTC),
                    started_at=now,
                    error=None,
                )
            )
            if claimed.rowcount == 0:
                session.rollback()
                return None
            session.commit()
            return session.get(JobRequest, candidate.id)

    def heartbeat_job_request(self, *, request_id: str, lease_owner: str, lease_seconds: int = 1800) -> None:
        with self.session_factory() as session:
            row = session.get(JobRequest, request_id)
            if row is None or row.status != JobRequestStatus.RUNNING.value or row.lease_owner != lease_owner:
                return
            row.lease_expires_at = datetime.fromtimestamp(datetime.now(UTC).timestamp() + lease_seconds, UTC)
            session.commit()

    def complete_job_request(self, request_id: str, *, result: dict | None = None, run_id: str | None = None) -> None:
        with self.session_factory() as session:
            row = session.get(JobRequest, request_id)
            if row is None:
                return
            row.status = JobRequestStatus.SUCCEEDED.value
            row.result = result or {}
            row.run_id = run_id
            row.finished_at = datetime.now(UTC)
            row.lease_owner = None
            row.lease_expires_at = None
            session.commit()

    def fail_job_request(self, request_id: str, *, error: str, result: dict | None = None, run_id: str | None = None) -> None:
        with self.session_factory() as session:
            row = session.get(JobRequest, request_id)
            if row is None:
                return
            row.status = JobRequestStatus.FAILED.value
            row.error = error
            row.result = result or {}
            row.run_id = run_id
            row.finished_at = datetime.now(UTC)
            row.lease_owner = None
            row.lease_expires_at = None
            session.commit()

    def recover_expired_job_requests(self, *, now: datetime | None = None) -> int:
        effective_now = now or datetime.now(UTC)
        with self.session_factory() as session:
            rows = session.scalars(
                select(JobRequest).where(
                    JobRequest.status == JobRequestStatus.RUNNING.value,
                    JobRequest.lease_expires_at.is_not(None),
                    JobRequest.lease_expires_at < effective_now,
                )
            ).all()
            for row in rows:
                row.status = JobRequestStatus.FAILED.value
                row.error = "Recovered after runner lease expired."
                row.finished_at = effective_now
                row.lease_owner = None
                row.lease_expires_at = None
            session.commit()
            return len(rows)

    def count_active_job_requests(self) -> int:
        active_statuses = {JobRequestStatus.QUEUED.value, JobRequestStatus.RUNNING.value}
        with self.session_factory() as session:
            from sqlalchemy import func
            return session.scalar(
                select(func.count(JobRequest.id))
                .where(JobRequest.status.in_(active_statuses))
            ) or 0

    def list_job_requests(self, limit: int | None = None) -> list[JobRequest]:
        with self.session_factory() as session:
            stmt = select(JobRequest).order_by(JobRequest.requested_at.desc(), JobRequest.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def get_job_request(self, request_id: str) -> JobRequest | None:
        with self.session_factory() as session:
            return session.get(JobRequest, request_id)

    def record_service_heartbeat(self, *, service_name: str, instance_id: str, details: dict | None = None) -> ServiceHeartbeat:
        with self.session_factory() as session:
            row = session.get(ServiceHeartbeat, service_name)
            if row is None:
                row = ServiceHeartbeat(service_name=service_name, instance_id=instance_id)
                session.add(row)
            row.instance_id = instance_id
            row.last_seen = datetime.now(UTC)
            row.details = details or {}
            session.commit()
            session.refresh(row)
            return row

    def get_service_heartbeat(self, service_name: str) -> ServiceHeartbeat | None:
        with self.session_factory() as session:
            return session.get(ServiceHeartbeat, service_name)

    def abort_stale_jobs(self, now: datetime) -> int:
        _ = now
        with self.session_factory() as session:
            return mark_stale_running_jobs(session)

    def reconcile_portfolio_from_fills(self) -> PortfolioSnapshot:
        with self.session_factory() as session:
            ledger = reconcile_trade_ledger(session, starting_cash=get_settings().market.initial_capital)
            self._replace_positions(session, ledger.positions)
            snapshot = snapshot_from_ledger(ledger)
            session.commit()
            return snapshot

    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        with self.session_factory() as session:
            return reconcile_portfolio(session, starting_cash=get_settings().market.initial_capital)

    def portfolio_ledger(self, *, as_of: date | None = None) -> PortfolioLedger:
        with self.session_factory() as session:
            return reconcile_trade_ledger(session, starting_cash=get_settings().market.initial_capital, as_of=as_of)

    def open_shares_for_ticker(self, ticker: str) -> int:
        return self.portfolio_ledger().shares_for_ticker(ticker)

    def _replace_positions(self, session: Session, positions: list[PositionProjection]) -> None:
        existing = {row.ticker: row for row in session.scalars(select(Position)).all()}
        live_tickers = {row.ticker for row in positions}
        for ticker, row in existing.items():
            if ticker not in live_tickers:
                session.delete(row)
        for projection in positions:
            row = existing.get(projection.ticker)
            if row is None:
                row = Position(ticker=projection.ticker)
                session.add(row)
            row.shares = projection.shares
            row.avg_entry_price = projection.avg_entry_price
            row.total_cost = projection.total_cost
            row.sector = projection.sector
            row.stop_loss_price = projection.stop_loss_price
            row.trailing_stop_price = projection.trailing_stop_price
            row.position_type = projection.position_type
            row.last_updated = projection.last_updated

    def get_runtime_state(self) -> dict[str, object]:
        with self.session_factory() as session:
            state = session.get(RuntimeState, 1)
            if state is None:
                state = RuntimeState(id=1)
                session.add(state)
                session.commit()
            return {
                "autonomy_paused": bool(state.autonomy_paused),
                "entries_blocked": bool(state.entries_blocked),
                "exits_only": bool(state.exits_only),
                "updated_at": state.updated_at,
                "updated_reason": state.updated_reason,
            }

    def update_runtime_state(
        self,
        *,
        autonomy_paused: bool | None = None,
        entries_blocked: bool | None = None,
        exits_only: bool | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        with self.session_factory() as session:
            state = session.get(RuntimeState, 1)
            if state is None:
                state = RuntimeState(id=1)
                session.add(state)
            if autonomy_paused is not None:
                state.autonomy_paused = int(autonomy_paused)
            if entries_blocked is not None:
                state.entries_blocked = int(entries_blocked)
            if exits_only is not None:
                state.exits_only = int(exits_only)
            state.updated_at = datetime.now(UTC)
            if reason is not None:
                state.updated_reason = reason
            session.commit()
        return self.get_runtime_state()

    def get_full_runtime_state(self) -> dict[str, object]:
        now = datetime.now(UTC)
        with self.session_factory() as session:
            # 1. Sync and get runtime state
            state = session.get(RuntimeState, 1)
            if state is None:
                state = RuntimeState(id=1)
                session.add(state)

            pause_messages = session.scalars(
                select(DeskMessage).where(
                    DeskMessage.status == "active",
                    DeskMessage.effective_from <= now,
                    or_(DeskMessage.expires_at.is_(None), DeskMessage.expires_at >= now),
                )
            ).all()

            pause_active = any((row.parsed_intent or {}).get("kind") == "pause_entries" for row in pause_messages)
            if bool(state.entries_blocked) != pause_active:
                state.entries_blocked = int(pause_active)
                state.updated_at = datetime.now(UTC)
                state.updated_reason = "Desk message requested entry pause." if pause_active else "Entry pause cleared."
                session.commit()

            # 2. Get other components
            overrides = {row.key: row.value for row in session.scalars(
                select(RuntimeOverride).where(
                    RuntimeOverride.enabled == 1,
                    RuntimeOverride.effective_from <= now,
                    or_(RuntimeOverride.expires_at.is_(None), RuntimeOverride.expires_at >= now),
                )
            ).all()}

            # 3. Get memory prompts (simplified)
            prompts: dict[str, str] = {}
            from quant_trading.memory.graph import GraphMemory
            from quant_trading.memory.structured import latest_lessons
            graph = GraphMemory(session)
            agent_ids = {row.agent_id for row in session.scalars(select(Reflection)).all()}
            for agent_id in sorted(agent_ids):
                lessons = latest_lessons(session=session, agent_id=agent_id, limit=8)
                hits = graph.search_hits(query=f"{agent_id} responsibility root cause outcome", limit=5)
                lines = ["Recent lessons:"]
                lines.extend(f"- {lesson}" for lesson in lessons) if lessons else lines.append("- No recent lessons.")
                lines.append("Similar episodes:")
                lines.extend(f"- {h.content}" for h in hits) if hits else lines.append("- No similar episodes.")
                prompts[agent_id] = "\n".join(lines)

            return {
                "runtime_state": {
                    "autonomy_paused": bool(state.autonomy_paused),
                    "entries_blocked": bool(state.entries_blocked),
                    "exits_only": bool(state.exits_only),
                },
                "overrides": overrides,
                "desk_messages": [
                    {"text": row.raw_text, "intent": row.parsed_intent}
                    for row in pause_messages
                ],
                "memory_context": prompts,
            }

    def sync_entries_blocked_from_desk_messages(self) -> dict[str, object]:
        now = datetime.now(UTC)
        with self.session_factory() as session:
            state = session.get(RuntimeState, 1)
            if state is None:
                state = RuntimeState(id=1)
                session.add(state)
            pause_messages = session.scalars(
                select(DeskMessage).where(
                    DeskMessage.status == "active",
                    DeskMessage.effective_from <= now,
                    or_(DeskMessage.expires_at.is_(None), DeskMessage.expires_at >= now),
                )
            ).all()
            pause_active = any((row.parsed_intent or {}).get("kind") == "pause_entries" for row in pause_messages)
            if bool(state.entries_blocked) != pause_active:
                state.entries_blocked = int(pause_active)
                state.updated_at = datetime.now(UTC)
                if pause_active:
                    state.updated_reason = "Desk message requested entry pause."
                elif state.updated_reason == "Desk message requested entry pause.":
                    state.updated_reason = "Entry pause cleared."
                session.commit()
        return self.get_runtime_state()

    def record_agent_run(self, result: AgentResult) -> None:
        with self.session_factory() as session:
            session.merge(
                AgentRun(
                    id=str(uuid4()),
                    run_id=result.run_id,
                    agent_id=result.agent_id,
                    status=result.status.value,
                    started_at=result.started_at,
                    finished_at=result.finished_at,
                    warnings=result.warnings,
                    artifacts=result.artifacts,
                )
            )
            for ticker, score in result.scores_by_ticker.items():
                session.add(
                    SignalHistory(
                        signal_date=result.started_at.date(),
                        run_id=result.run_id,
                        agent_id=result.agent_id,
                        ticker=ticker,
                        score=score,
                        details=result.artifacts,
                    )
                )
            session.commit()

    def record_trade_decisions(self, run_id: str, decisions: list[TradeDecision]) -> list[str]:
        ids: list[str] = []
        with self.session_factory() as session:
            for decision in decisions:
                decision_id = str(uuid4())
                ids.append(decision_id)
                session.add(
                    TradeDecisionRecord(
                        id=decision_id,
                        run_id=run_id,
                        ticker=decision.ticker,
                        decision=decision.decision.value,
                        position_type=decision.position_type.value,
                        shares=decision.shares,
                        confidence=decision.confidence,
                        origin=decision.origin,
                        payload=decision.model_dump(mode="json"),
                    )
                )
            session.commit()
        return ids

    def record_trade_decision(self, run_id: str, decision: TradeDecision) -> str:
        order_id = str(uuid4())
        with self.session_factory() as session:
            session.add(
                Order(
                    id=order_id,
                    run_id=run_id,
                    ticker=decision.ticker,
                    decision=decision.decision.value,
                    position_type=decision.position_type.value,
                    shares=decision.shares,
                    confidence=decision.confidence,
                    payload=decision.model_dump(mode="json"),
                )
            )
            session.commit()
        return order_id

    def record_fill(
        self,
        order_id: str,
        run_id: str,
        ticker: str,
        action: str,
        shares: int,
        fill_price: float,
        charges: float,
        execution_type: str,
        metadata: dict | None = None,
    ) -> str:
        fill_id = str(uuid4())
        with self.session_factory() as session:
            session.add(
                Fill(
                    id=fill_id,
                    order_id=order_id,
                    run_id=run_id,
                    ticker=ticker,
                    action=action,
                    shares=shares,
                    fill_price=fill_price,
                    charges=charges,
                    execution_type=execution_type,
                    details=metadata or {},
                )
            )
            session.commit()
        return fill_id

    def execute_trade_decision(self, run_id: str, decision: TradeDecision, price: PriceData, universe_item: UniverseItem | None = None) -> str:
        if decision.decision.value == "SELL":
            available_shares = self.open_shares_for_ticker(decision.ticker)
            if available_shares < decision.shares:
                raise ValueError(f"Unable to sell {decision.shares} shares of {decision.ticker}; only {available_shares} shares are open.")
        order_id = self.record_trade_decision(run_id=run_id, decision=decision)
        market_cap_cr = universe_item.market_cap_cr if universe_item else None
        if decision.decision.value == "BUY":
            fill_price = compute_entry_fill(price, market_cap_cr=market_cap_cr)
        else:
            fill_price = compute_exit_fill(price, market_cap_cr=market_cap_cr, ltp=price.last_price, defensive=False)
        trade_value = fill_price * decision.shares
        schedule = self.latest_charge_schedule()
        charges = compute_delivery_charges(schedule, trade_value=trade_value, action=decision.decision.value)
        fill_id = self.record_fill(
            order_id=order_id,
            run_id=run_id,
            ticker=decision.ticker,
            action=decision.decision.value,
            shares=decision.shares,
            fill_price=fill_price,
            charges=charges.total,
            execution_type=decision.entry_policy.fill_model,
            metadata={
                "reason_code": decision.reason_code,
                "sector": universe_item.sector if universe_item else None,
                "position_type": decision.position_type.value,
                "stop_loss_price": decision.stop_policy.hard_stop_price,
                "trailing_stop_price": decision.stop_policy.trailing_stop_price,
            },
        )
        self.apply_fill_to_positions(
            ticker=decision.ticker,
            action=decision.decision.value,
            shares=decision.shares,
            fill_price=fill_price,
            charges=charges.total,
            sector=universe_item.sector if universe_item else None,
            position_type=decision.position_type.value,
            stop_loss_price=decision.stop_policy.hard_stop_price,
            trailing_stop_price=decision.stop_policy.trailing_stop_price,
        )
        return fill_id

    def apply_fill_to_positions(
        self,
        ticker: str,
        action: str,
        shares: int,
        fill_price: float,
        charges: float,
        sector: str | None,
        position_type: str,
        stop_loss_price: float | None,
        trailing_stop_price: float | None,
    ) -> None:
        _ = (ticker, action, shares, fill_price, charges, sector, position_type, stop_loss_price, trailing_stop_price)
        self.reconcile_portfolio_from_fills()

    def latest_ic_map(self) -> dict[str, float]:
        snapshot = self.latest_ic_snapshot()
        return {agent_id: data["ic_value"] for agent_id, data in snapshot.items()}

    def latest_ic_snapshot(self) -> dict[str, dict[str, float | int | bool | None]]:
        with self.session_factory() as session:
            rows = session.scalars(select(AgentICHistory).order_by(AgentICHistory.ic_date.desc(), AgentICHistory.id.desc())).all()
            snapshot: dict[str, dict[str, float | int | bool | None]] = {}
            for row in rows:
                if row.agent_id in snapshot:
                    continue
                details = row.details or {}
                snapshot[row.agent_id] = {
                    "ic_value": row.ic_value,
                    "win_rate": row.win_rate,
                    "avg_rr": row.avg_rr,
                    "sample_size": int(details.get("sample_size", details.get("observations", 0)) or 0),
                    "sample_size_10d": int(details.get("sample_size_10d", 0) or 0),
                    "ic_weight": details.get("ic_weight"),
                    "ic_10d": details.get("ic_10d"),
                    "decay_lambda": details.get("decay_lambda"),
                    "active": bool(details.get("active", row.ic_value >= 0.04)),
                }
            return snapshot

    def replace_ic_history(self, ic_date: date, rows: list[dict]) -> None:
        with self.session_factory() as session:
            session.execute(delete(AgentICHistory).where(AgentICHistory.ic_date == ic_date))
            for row in rows:
                session.add(
                    AgentICHistory(
                        ic_date=ic_date,
                        agent_id=row["agent_id"],
                        ic_value=row["ic_value"],
                        win_rate=row.get("win_rate"),
                        avg_rr=row.get("avg_rr"),
                        details=row.get("details", {}),
                    )
                )
            session.commit()

    def replace_agent_signal_outcomes(self, trade_id: str, rows: list[dict]) -> None:
        with self.session_factory() as session:
            session.execute(delete(AgentSignalOutcome).where(AgentSignalOutcome.trade_id == trade_id))
            for row in rows:
                session.add(
                    AgentSignalOutcome(
                        trade_id=trade_id,
                        agent_id=row["agent_id"],
                        ticker=row["ticker"],
                        outcome_5d=row.get("outcome_5d"),
                        outcome_10d=row.get("outcome_10d"),
                        directionally_correct=row.get("directionally_correct"),
                        was_decisive=row.get("was_decisive"),
                        responsibility=row.get("responsibility"),
                        details=row.get("details", {}),
                    )
                )
            session.commit()

    def list_signal_history(self, agent_id: str | None = None, ticker: str | None = None, limit: int | None = None) -> list[SignalHistory]:
        with self.session_factory() as session:
            stmt = select(SignalHistory).order_by(SignalHistory.signal_date.desc(), SignalHistory.id.desc())
            if agent_id:
                stmt = stmt.where(SignalHistory.agent_id == agent_id)
            if ticker:
                stmt = stmt.where(SignalHistory.ticker == ticker)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_fills(self, limit: int | None = None) -> list[Fill]:
        with self.session_factory() as session:
            stmt = select(Fill).order_by(Fill.created_at.desc(), Fill.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_positions(self) -> list[Position]:
        with self.session_factory() as session:
            return list(session.scalars(select(Position).order_by(Position.ticker.asc())).all())

    def list_orders(self, limit: int | None = None) -> list[Order]:
        with self.session_factory() as session:
            stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_trade_decisions(self, run_id: str | None = None, decision: str | None = None, limit: int | None = None) -> list[TradeDecisionRecord]:
        with self.session_factory() as session:
            stmt = select(TradeDecisionRecord).order_by(TradeDecisionRecord.created_at.desc(), TradeDecisionRecord.id.desc())
            if run_id:
                stmt = stmt.where(TradeDecisionRecord.run_id == run_id)
            if decision:
                stmt = stmt.where(TradeDecisionRecord.decision == decision)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_job_runs(self, limit: int | None = None) -> list[JobRun]:
        with self.session_factory() as session:
            stmt = select(JobRun).order_by(JobRun.started_at.desc(), JobRun.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_agent_runs(self, run_id: str | None = None, agent_id: str | None = None, limit: int | None = None) -> list[AgentRun]:
        with self.session_factory() as session:
            stmt = select(AgentRun).order_by(AgentRun.started_at.desc(), AgentRun.id.desc())
            if run_id:
                stmt = stmt.where(AgentRun.run_id == run_id)
            if agent_id:
                stmt = stmt.where(AgentRun.agent_id == agent_id)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_daily_marks(self, limit: int | None = None) -> list[DailyMark]:
        with self.session_factory() as session:
            stmt = select(DailyMark).order_by(DailyMark.mark_date.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_reflections(self, agent_id: str | None = None, limit: int | None = None) -> list[Reflection]:
        with self.session_factory() as session:
            stmt = select(Reflection).order_by(Reflection.reflection_date.desc(), Reflection.id.desc())
            if agent_id:
                stmt = stmt.where(Reflection.agent_id == agent_id)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_ic_history(self, agent_id: str | None = None, limit: int | None = None) -> list[AgentICHistory]:
        with self.session_factory() as session:
            stmt = select(AgentICHistory).order_by(AgentICHistory.ic_date.desc(), AgentICHistory.id.desc())
            if agent_id:
                stmt = stmt.where(AgentICHistory.agent_id == agent_id)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def list_signal_outcomes(self, trade_id: str | None = None, agent_id: str | None = None, ticker: str | None = None, limit: int | None = None) -> list[AgentSignalOutcome]:
        with self.session_factory() as session:
            stmt = select(AgentSignalOutcome).order_by(AgentSignalOutcome.id.desc())
            if trade_id:
                stmt = stmt.where(AgentSignalOutcome.trade_id == trade_id)
            if agent_id:
                stmt = stmt.where(AgentSignalOutcome.agent_id == agent_id)
            if ticker:
                stmt = stmt.where(AgentSignalOutcome.ticker == ticker)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def get_order_payload(self, order_id: str) -> dict:
        with self.session_factory() as session:
            order = session.get(Order, order_id)
            return dict(order.payload or {}) if order else {}

    def get_memory_prompts(self) -> dict[str, str]:
        with self.session_factory() as session:
            prompts: dict[str, str] = {}
            graph = GraphMemory(session)
            agent_ids = {
                row.agent_id
                for row in session.scalars(select(Reflection).order_by(Reflection.reflection_date.desc())).all()
            }
            for agent_id in sorted(agent_ids):
                lessons = latest_lessons(session=session, agent_id=agent_id, limit=8)
                hits = graph.search_hits(query=f"{agent_id} responsibility root cause outcome", limit=5)
                lines = ["Recent lessons:"]
                if lessons:
                    lines.extend(f"- {lesson}" for lesson in lessons)
                else:
                    lines.append("- No recent lessons.")
                lines.append("Similar episodes:")
                if hits:
                    for hit in hits:
                        lines.append(f"- {hit.content}")
                else:
                    lines.append("- No similar episodes.")
                prompts[agent_id] = "\n".join(lines)
            return prompts

    def search_memory(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        with self.session_factory() as session:
            graph = GraphMemory(session)
            return [
                {
                    "ref_id": hit.ref_id,
                    "content": hit.content,
                    "node_type": hit.node_type,
                    "score": hit.score,
                }
                for hit in graph.search_hits(query=query, limit=limit)
            ]

    def list_desk_messages(self, active_only: bool = False, limit: int | None = None) -> list[DeskMessage]:
        now = datetime.now(UTC)
        with self.session_factory() as session:
            stmt = select(DeskMessage).order_by(DeskMessage.created_at.desc(), DeskMessage.id.desc())
            if active_only:
                stmt = stmt.where(
                    DeskMessage.status == "active",
                    DeskMessage.effective_from <= now,
                    or_(DeskMessage.expires_at.is_(None), DeskMessage.expires_at >= now),
                )
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def create_desk_message(
        self,
        raw_text: str,
        *,
        scope: str = "global",
        status: str = "active",
        effective_from: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> DeskMessage:
        with self.session_factory() as session:
            row = DeskMessage(
                scope=scope,
                status=status,
                raw_text=raw_text,
                parsed_intent=_parse_desk_message(raw_text),
                effective_from=effective_from or datetime.now(UTC),
                expires_at=expires_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def deactivate_desk_message(self, message_id: str) -> None:
        with self.session_factory() as session:
            row = session.get(DeskMessage, message_id)
            if row is None:
                return
            row.status = "revoked"
            session.commit()

    def revoke_desk_message(self, message_id: str) -> DeskMessage | None:
        with self.session_factory() as session:
            row = session.get(DeskMessage, message_id)
            if row is None:
                return None
            row.status = "revoked"
            session.commit()
            session.refresh(row)
            return row

    def active_runtime_overrides(self) -> dict[str, object]:
        now = datetime.now(UTC)
        with self.session_factory() as session:
            stmt = select(RuntimeOverride).where(
                RuntimeOverride.enabled == 1,
                RuntimeOverride.effective_from <= now,
                or_(RuntimeOverride.expires_at.is_(None), RuntimeOverride.expires_at >= now),
            )
            rows = session.scalars(stmt).all()
            return {row.key: row.value for row in rows}

    def get_runtime_overrides(self) -> dict[str, object]:
        return self.active_runtime_overrides()

    def create_runtime_override(
        self,
        *,
        key: str,
        value: dict | list | str | int | float | bool | None,
        scope: str = "global",
        enabled: bool = True,
        effective_from: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> RuntimeOverride:
        with self.session_factory() as session:
            row = RuntimeOverride(
                key=key,
                value=value if isinstance(value, dict) else {"value": value},
                scope=scope,
                enabled=int(enabled),
                effective_from=effective_from or datetime.now(UTC),
                expires_at=expires_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def list_runtime_overrides(self, limit: int | None = None) -> list[RuntimeOverride]:
        with self.session_factory() as session:
            stmt = select(RuntimeOverride).order_by(RuntimeOverride.created_at.desc(), RuntimeOverride.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def log_operator_action(self, action: str, payload: dict | None = None) -> OperatorAction:
        with self.session_factory() as session:
            row = OperatorAction(action=action, payload=payload or {})
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def list_operator_actions(self, limit: int | None = None) -> list[OperatorAction]:
        with self.session_factory() as session:
            stmt = select(OperatorAction).order_by(OperatorAction.created_at.desc(), OperatorAction.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def get_overview_snapshot(self) -> dict[str, object]:
        latest_marks = self.list_daily_marks(limit=10)
        latest_mark = latest_marks[0] if latest_marks else None
        return {
            "runtime_state": self.get_runtime_state(),
            "portfolio": self.get_portfolio_snapshot().model_dump(mode="json"),
            "latest_mark": {
                "mark_date": latest_mark.mark_date.isoformat(),
                "portfolio_value": latest_mark.portfolio_value,
                "cash_balance": latest_mark.cash_balance,
                "realized_pnl": latest_mark.realized_pnl,
                "realized_pnl_today": latest_mark.realized_pnl,
                "total_realized_pnl": latest_mark.total_realized_pnl,
                "unrealized_pnl": latest_mark.unrealized_pnl,
                "benchmark_close": latest_mark.benchmark_close,
                "benchmark_return_pct": latest_mark.benchmark_return_pct,
                "alpha_pct": latest_mark.alpha_pct,
                "details": latest_mark.details or {},
            }
            if latest_mark
            else None,
            "positions": [
                {
                    "ticker": position.ticker,
                    "shares": position.shares,
                    "avg_entry_price": position.avg_entry_price,
                    "total_cost": position.total_cost,
                    "position_type": position.position_type,
                    "stop_loss_price": position.stop_loss_price,
                    "trailing_stop_price": position.trailing_stop_price,
                }
                for position in self.list_positions()
            ],
            "recent_jobs": [
                {
                    "id": row.id,
                    "job_name": row.job_name,
                    "status": row.status,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                    "payload": row.payload or {},
                    "error": row.error,
                }
                for row in self.list_job_runs(limit=15)
            ],
            "recent_decisions": [
                {
                    "id": row.id,
                    "run_id": row.run_id,
                    "ticker": row.ticker,
                    "decision": row.decision,
                    "position_type": row.position_type,
                    "shares": row.shares,
                    "confidence": row.confidence,
                    "origin": row.origin,
                    "payload": row.payload or {},
                    "created_at": row.created_at.isoformat(),
                }
                for row in self.list_trade_decisions(limit=10)
            ],
            "active_desk_messages": [
                {
                    "id": row.id,
                    "scope": row.scope,
                    "raw_text": row.raw_text,
                    "parsed_intent": row.parsed_intent or {},
                    "created_at": row.created_at.isoformat(),
                    "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                }
                for row in self.list_desk_messages(active_only=True, limit=10)
            ],
            "recent_operator_actions": [
                {
                    "id": row.id,
                    "action": row.action,
                    "payload": row.payload or {},
                    "created_at": row.created_at.isoformat(),
                }
                for row in self.list_operator_actions(limit=10)
            ],
        }

    def record_reflection_job(self, agent_id: str) -> None:
        with self.session_factory() as session:
            session.add(
                Reflection(
                    reflection_date=market_today(),
                    agent_id=agent_id,
                    summary=f"Placeholder reflection for {agent_id}",
                    lessons=[ReflectionLesson(agent_id=agent_id, headline="Bootstrapped", lesson="System scaffolded.").model_dump()],
                )
            )
            session.commit()

    def latest_charge_schedule(self, broker: str = "zerodha", venue: str = "NSE", product: str = "CNC") -> dict:
        with self.session_factory() as session:
            return latest_charge_schedule(session, broker=broker, venue=venue, product=product).schedule

    def mark_portfolio(
        self,
        price_map: dict[str, float],
        mark_date: date | None = None,
        benchmark_close: float | None = None,
        benchmark_return_pct: float | None = None,
        alpha_pct: float | None = None,
        details: dict | None = None,
        persist: bool = True,
    ) -> PortfolioSnapshot:
        active_mark_date = mark_date or market_today()
        with self.session_factory() as session:
            ledger = reconcile_trade_ledger(session, starting_cash=get_settings().market.initial_capital, as_of=active_mark_date)
            snapshot = snapshot_from_ledger(ledger, price_map=price_map)
            if persist:
                daily_mark = session.get(DailyMark, active_mark_date)
                if daily_mark is None:
                    daily_mark = DailyMark(mark_date=active_mark_date)
                    session.add(daily_mark)
                daily_mark.portfolio_value = snapshot.portfolio_value
                daily_mark.cash_balance = snapshot.cash_balance
                daily_mark.realized_pnl = ledger.realized_pnl_by_date.get(active_mark_date, 0.0)
                daily_mark.total_realized_pnl = snapshot.total_realized_pnl
                daily_mark.unrealized_pnl = snapshot.total_unrealized_pnl
                daily_mark.benchmark_close = benchmark_close
                daily_mark.benchmark_return_pct = benchmark_return_pct
                daily_mark.alpha_pct = alpha_pct
                daily_mark.details = {
                    "priced_positions": snapshot.priced_positions,
                    "unpriced_positions": snapshot.unpriced_positions,
                    "price_map": price_map,
                    **(details or {}),
                }
                session.commit()
            return snapshot
