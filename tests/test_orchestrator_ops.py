from __future__ import annotations

from datetime import UTC, date, datetime, time
from pathlib import Path

from quant_trading.config import get_settings
from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.orchestrator import Orchestrator, PIPELINE_SEQUENCE
from quant_trading.schemas import AgentResult, AgentStatus, DecisionType, EntryPolicy, PositionType, PriceBar, PriceData, SessionState, StopPolicy, TradeDecision
from quant_trading.services.market_clock import MarketSnapshot
from quant_trading.tools.yfinance_client import YFinanceClient


def write_holiday_calendar(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "nse_holidays_2026.json").write_text(
        '{"year": 2026, "fetched_at": "2026-03-01T00:00:00+00:00", "holidays": [{"date": "2026-01-26"}]}',
        encoding="utf-8",
    )


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


class FakeMarketData(YFinanceClient):
    def __init__(self) -> None:
        super().__init__(cache_ttl_seconds=3600)

    def load_price_data(self, ticker: str, period: str = "6mo") -> PriceData:
        _ = period
        last_price = 100.0
        return PriceData(
            ticker=ticker,
            last_price=last_price,
            previous_bar=PriceBar(
                open=99.0,
                high=101.0,
                low=98.0,
                close=100.0,
                volume=1_000_000,
                as_of=datetime(2026, 3, 6, 9, 15, tzinfo=UTC),
            ),
            history=[],
        )


class DummyAgent:
    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def run(self, context):  # noqa: ANN001
        artifacts = {}
        if self.agent_id == "agent_01_universe":
            artifacts["universe"] = [{"ticker": "RELIANCE", "sector": "Energy", "market_cap_cr": 1000.0}]
        elif self.agent_id == "agent_02_quality":
            artifacts["qualified_universe"] = [{"ticker": "RELIANCE", "sector": "Energy", "market_cap_cr": 1000.0}]
        return AgentResult(
            agent_id=self.agent_id,
            run_id=context.run_id,
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"RELIANCE": 0.9} if self.agent_id in {"agent_03_momentum", "agent_13_risk"} else {},
            artifacts=artifacts,
            warnings=[],
            started_at=datetime(2026, 3, 6, 4, 30, tzinfo=UTC),
            finished_at=datetime(2026, 3, 6, 4, 30, tzinfo=UTC),
        )


class DummyBoss:
    def run(self, context):  # noqa: ANN001
        return [
            TradeDecision(
                decision=DecisionType.BUY,
                ticker="RELIANCE",
                position_type=PositionType.QUALITY,
                target_weight=0.05,
                shares=10,
                entry_policy=EntryPolicy(fill_model="prev_session_hlc3", valid_until=time(15, 0)),
                stop_policy=StopPolicy(hard_stop_price=93.0),
                confidence=0.9,
                reason_code="test_buy",
            )
        ]


def build_orchestrator(monkeypatch, tmp_path: Path) -> Orchestrator:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    get_settings.cache_clear()
    write_holiday_calendar(tmp_path)
    repository = build_repository()
    agents = {agent_id: DummyAgent(agent_id) for agent_id in PIPELINE_SEQUENCE}
    orchestrator = Orchestrator(repository=repository, agents=agents, boss=DummyBoss(), market_data=FakeMarketData(), gateway=None)
    orchestrator.holidays.refresh_if_needed = lambda now=None: tmp_path / "data" / "nse_holidays_2026.json"  # type: ignore[method-assign]
    return orchestrator


def open_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        timestamp_utc=datetime(2026, 3, 6, 4, 30, tzinfo=UTC),
        date_local=date(2026, 3, 6),
        time_local=time(10, 0),
        session_state=SessionState.OPEN,
        is_market_day=True,
        calendar_ready=True,
        holiday_status="ready",
        holiday_error=None,
    )


def test_pipeline_slot_lock_blocks_duplicate_run(monkeypatch, tmp_path: Path) -> None:
    orchestrator = build_orchestrator(monkeypatch, tmp_path)
    orchestrator.market_clock.snapshot = lambda now=None: open_snapshot()  # type: ignore[method-assign]

    first = orchestrator.run_pipeline(trigger="morning-pipeline")
    second = orchestrator.run_pipeline(trigger="morning-pipeline")

    assert first.run_id == second.run_id
    assert len(orchestrator.repository.list_fills()) == 1
    slots = orchestrator.repository.list_trading_slots(slot_date=date(2026, 3, 6))
    assert len(slots) == 1
    assert slots[0].status == "succeeded"


def test_startup_recovery_catches_up_missed_slot(monkeypatch, tmp_path: Path) -> None:
    orchestrator = build_orchestrator(monkeypatch, tmp_path)
    orchestrator.market_clock.snapshot = lambda now=None: open_snapshot()  # type: ignore[method-assign]

    orchestrator.startup_recovery()

    slots = orchestrator.repository.list_trading_slots(slot_date=date(2026, 3, 6))
    assert [slot.slot_name for slot in slots] == ["morning-pipeline"]
    actions = orchestrator.repository.list_operator_actions(limit=10)
    assert any(action.action == "startup.catchup_ran" for action in actions)
