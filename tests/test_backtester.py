from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from quant_trading.db.models import AgentICHistory, AgentSignalOutcome, Fill, MemoryNode, SignalHistory
from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.schemas import AgentResult, AgentStatus, DecisionType, EntryPolicy, PositionType, PriceBar, PriceData, StopPolicy, TradeDecision
from quant_trading.services.backtester import BacktesterService


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


class FakeMarketData:
    def __init__(self) -> None:
        self.series = {}
        start = datetime(2026, 1, 1, tzinfo=UTC)
        closes = [100 + idx for idx in range(30)]
        self.series["RELIANCE.NS"] = PriceData(
            ticker="RELIANCE.NS",
            last_price=closes[-1],
            history=[
                PriceBar(
                    open=value - 1,
                    high=value + 1,
                    low=value - 2,
                    close=value,
                    volume=1_000_000,
                    as_of=start + timedelta(days=idx),
                )
                for idx, value in enumerate(closes)
            ],
        )

    def load_price_data(self, ticker: str, period: str = "2y") -> PriceData:
        _ = period
        return self.series[ticker]


def test_backtester_backfills_ic_and_trade_attribution() -> None:
    repository = build_repository()
    signal_time = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
    run_id = "run-backfill"
    repository.record_agent_run(
        AgentResult(
            agent_id="agent_03_momentum",
            run_id=run_id,
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"RELIANCE": 0.8},
            artifacts={},
            warnings=[],
            started_at=signal_time,
            finished_at=signal_time,
        )
    )
    repository.record_agent_run(
        AgentResult(
            agent_id="agent_08_ownership",
            run_id=run_id,
            status=AgentStatus.SUCCESS,
            scores_by_ticker={"RELIANCE": 0.4},
            artifacts={},
            warnings=[],
            started_at=signal_time,
            finished_at=signal_time,
        )
    )
    with repository.session_factory() as session:
        for idx in range(1, 6):
            session.add(
                SignalHistory(
                    signal_date=(signal_time - timedelta(days=idx)).date(),
                    run_id=f"history-{idx}",
                    agent_id="agent_03_momentum",
                    ticker="RELIANCE",
                    score=0.2 + (idx * 0.1),
                    details={},
                )
            )
        session.commit()
    order_id = repository.record_trade_decision(
        run_id=run_id,
        decision=TradeDecision(
            decision=DecisionType.BUY,
            ticker="RELIANCE",
            position_type=PositionType.MOMENTUM,
            target_weight=0.05,
            shares=10,
            entry_policy=EntryPolicy(fill_model="prev_session_hlc3"),
            stop_policy=StopPolicy(),
            confidence=0.7,
            reason_code="unit_test",
            active_agent_weights={"agent_03_momentum": 0.6, "agent_08_ownership": 0.4},
        ),
    )
    repository.record_fill(
        order_id=order_id,
        run_id=run_id,
        ticker="RELIANCE",
        action="BUY",
        shares=10,
        fill_price=100.0,
        charges=25.0,
        execution_type="PLANNED_DELIVERY",
    )
    with repository.session_factory() as session:
        fill = session.query(Fill).one()
        fill.created_at = signal_time
        session.commit()

    service = BacktesterService(session_factory=repository.session_factory, market_data=FakeMarketData(), conviction_threshold=0.6)
    summary = service.run_backfill(as_of=date(2026, 1, 25))

    assert summary.signal_rows_updated >= 2
    assert summary.attributed_trades == 1
    assert summary.ic_rows >= 1

    with repository.session_factory() as session:
        assert session.query(AgentICHistory).count() >= 1
        ic_row = session.query(AgentICHistory).filter(AgentICHistory.agent_id == "agent_03_momentum").first()
        assert ic_row is not None
        assert ic_row.details["sample_size"] >= 5
        assert ic_row.details["active"] is False
        assert ic_row.details["ic_weight"] == 0.0
        outcomes = session.query(AgentSignalOutcome).all()
        assert len(outcomes) == 2
        assert any(row.responsibility for row in outcomes)
        signal = session.query(SignalHistory).filter(SignalHistory.agent_id == "agent_03_momentum").first()
        assert signal is not None
        assert "forward_return_5d" in signal.details
        memory_nodes = session.query(MemoryNode).all()
        assert memory_nodes
        assert any("PRIMARY" in node.content for node in memory_nodes)
