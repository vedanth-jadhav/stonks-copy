from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, time
from pathlib import Path

from quant_trading.config import Settings
from quant_trading.db.models import AgentSignalOutcome, SignalHistory
from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.schemas import DecisionType, EntryPolicy, PositionType, StopPolicy, TradeDecision
from quant_trading.services.backtester import BacktesterService
from quant_trading.services.holiday_sync import HolidaySyncService
from quant_trading.services.pairs import PairsService, load_active_pairs
from quant_trading.tools.yfinance_client import YFinanceClient
from quant_trading.types import PriceBar, PriceData


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


class FakeMarketData(YFinanceClient):
    def __init__(self, history_map: dict[str, list[float]], start_date: date | None = None) -> None:
        self.history_map = history_map
        self.start_date = start_date or (datetime.now(UTC).date() - timedelta(days=30))

    def load_price_data(self, ticker: str, period: str = "6mo") -> PriceData:
        closes = self.history_map[ticker]
        start = datetime.combine(self.start_date, time(9, 15), tzinfo=UTC)
        bars = []
        for idx, close in enumerate(closes):
            when = start + timedelta(days=idx)
            bars.append(
                PriceBar(
                    open=close * 0.99,
                    high=close * 1.01,
                    low=close * 0.98,
                    close=close,
                    volume=1_000_000 + idx,
                    as_of=when,
                )
            )
        return PriceData(ticker=ticker, last_price=closes[-1], previous_bar=bars[-1], history=bars)


def test_backtester_backfills_ic_rows_and_trade_attribution() -> None:
    repository = build_repository()
    session_factory = repository.session_factory
    base_date = datetime.now(UTC).date() - timedelta(days=10)

    with session_factory() as session:
        for idx in range(6):
            session.add(
                SignalHistory(
                    signal_date=base_date + timedelta(days=idx),
                    run_id="run-a",
                    agent_id="agent_03_momentum",
                    ticker="RELIANCE",
                    score=0.2 + (idx * 0.1),
                    details={},
                )
            )
        session.add(
            SignalHistory(
                signal_date=base_date,
                run_id="run-a",
                agent_id="agent_09_sentiment",
                ticker="RELIANCE",
                score=0.3,
                details={},
            )
        )
        session.commit()

    order_id = repository.record_trade_decision(
        run_id="run-a",
        decision=TradeDecision(
            decision=DecisionType.BUY,
            ticker="RELIANCE",
            position_type=PositionType.MOMENTUM,
            target_weight=0.05,
            shares=10,
            entry_policy=EntryPolicy(fill_model="prev_session_hlc3", valid_until=time(15, 0)),
            stop_policy=StopPolicy(hard_stop_price=95.0),
            confidence=0.8,
            reason_code="test_backfill",
            active_agent_weights={"agent_03_momentum": 0.6, "agent_09_sentiment": 0.4},
        ),
    )
    repository.record_fill(
        order_id=order_id,
        run_id="run-a",
        ticker="RELIANCE",
        action="BUY",
        shares=10,
        fill_price=100.0,
        charges=10.0,
        execution_type="PLANNED_DELIVERY",
        metadata={},
    )

    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0, 116.0, 118.0]
    market_data = FakeMarketData({"RELIANCE.NS": closes, "RELIANCE": closes}, start_date=base_date - timedelta(days=2))
    summary = BacktesterService(repository=repository, market_data=market_data).run_backfill(as_of=date(2026, 1, 31))

    assert summary.signal_rows_updated >= 6
    assert summary.ic_rows >= 1
    assert summary.attributed_trades == 1
    snapshot = repository.latest_ic_snapshot()
    assert snapshot["agent_03_momentum"]["sample_size"] >= 5

    with session_factory() as session:
        outcomes = session.query(AgentSignalOutcome).filter(AgentSignalOutcome.trade_id == order_id).all()
        assert len(outcomes) == 2
        assert {row.agent_id for row in outcomes} == {"agent_03_momentum", "agent_09_sentiment"}


def test_pairs_service_writes_validated_pairs_file(monkeypatch, tmp_path: Path) -> None:
    import quant_trading.services.pairs as pairs_module

    monkeypatch.setattr(pairs_module, "_adf_pvalue", lambda spread: 0.01)
    monkeypatch.setattr(pairs_module, "_half_life", lambda spread: 10.0)

    prices_a = [100 + (idx * 0.8) for idx in range(140)]
    prices_b = [95 + (idx * 0.79) for idx in range(140)]
    market_data = FakeMarketData({"AAA.NS": prices_a, "BBB.NS": prices_b})
    output_path = tmp_path / "validated_pairs.json"
    service = PairsService(output_path=output_path, market_data=market_data, candidates=[("AAA", "BBB")])

    validations = service.revalidate()
    assert len(validations) == 1
    assert output_path.exists()
    pairs = load_active_pairs(output_path, fallback=[])
    assert pairs == [("AAA", "BBB")]


def test_holiday_sync_refreshes_local_cache(monkeypatch, tmp_path: Path) -> None:
    class FakeResponse:
        text = "Market holidays 2026 include 2026-01-26 and 2026-08-15."

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str) -> FakeResponse:
            _ = url
            return FakeResponse()

    monkeypatch.setattr("quant_trading.services.holiday_sync.httpx.Client", FakeClient)
    settings = Settings(data_dir=tmp_path)
    service = HolidaySyncService(settings)

    path = service.refresh(year=2026)
    payload = path.read_text()
    assert "2026-01-26" in payload
    assert "2026-08-15" in payload
