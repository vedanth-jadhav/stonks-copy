from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from quant_trading.db.models import DailyMark, Fill
from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.orchestrator import Orchestrator
from quant_trading.schemas import JobRunInput, JobStatus


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


def test_abort_stale_jobs_marks_running_rows_aborted() -> None:
    repository = build_repository()
    repository.create_job_run(
        JobRunInput(
            run_id="run-1",
            job_name="agent_03_momentum",
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
    )
    changed = repository.abort_stale_jobs(now=datetime.now(UTC))
    assert changed == 1


def test_default_charge_schedule_is_seeded() -> None:
    repository = build_repository()
    schedule = repository.latest_charge_schedule()
    assert schedule["stt_buy"] == 0.001
    assert schedule["dp_sell_flat"] == 15.93


def seed_fill(
    repository: QuantRepository,
    *,
    order_id: str,
    run_id: str,
    ticker: str,
    action: str,
    shares: int,
    fill_price: float,
    charges: float,
    created_at: datetime,
    metadata: dict | None = None,
) -> str:
    fill_id = repository.record_fill(
        order_id=order_id,
        run_id=run_id,
        ticker=ticker,
        action=action,
        shares=shares,
        fill_price=fill_price,
        charges=charges,
        execution_type="test",
        metadata=metadata,
    )
    with repository.session_factory() as session:
        fill = session.get(Fill, fill_id)
        assert fill is not None
        fill.created_at = created_at
        session.commit()
    repository.apply_fill_to_positions(
        ticker=ticker,
        action=action,
        shares=shares,
        fill_price=fill_price,
        charges=charges,
        sector=metadata.get("sector") if metadata else None,
        position_type=str((metadata or {}).get("position_type") or "QUALITY"),
        stop_loss_price=(metadata or {}).get("stop_loss_price"),
        trailing_stop_price=(metadata or {}).get("trailing_stop_price"),
    )
    return fill_id


def test_reconcile_portfolio_uses_fifo_lots_and_tracks_daily_realized() -> None:
    repository = build_repository()
    seed_fill(
        repository,
        order_id="order-1",
        run_id="run-1",
        ticker="RELIANCE",
        action="BUY",
        shares=10,
        fill_price=100.0,
        charges=10.0,
        created_at=datetime(2026, 3, 3, 4, 0, tzinfo=UTC),
        metadata={"position_type": "QUALITY", "sector": "Energy"},
    )
    seed_fill(
        repository,
        order_id="order-2",
        run_id="run-2",
        ticker="RELIANCE",
        action="BUY",
        shares=10,
        fill_price=120.0,
        charges=10.0,
        created_at=datetime(2026, 3, 4, 4, 0, tzinfo=UTC),
        metadata={"position_type": "QUALITY", "sector": "Energy"},
    )
    seed_fill(
        repository,
        order_id="order-3",
        run_id="run-3",
        ticker="RELIANCE",
        action="SELL",
        shares=15,
        fill_price=130.0,
        charges=15.0,
        created_at=datetime(2026, 3, 5, 4, 0, tzinfo=UTC),
    )

    snapshot = repository.reconcile_portfolio_from_fills()
    assert round(snapshot.cash_balance, 2) == 999_715.0
    assert round(snapshot.total_deployed, 2) == 605.0
    assert round(snapshot.total_realized_pnl, 2) == 320.0
    assert snapshot.open_positions == 1

    position = repository.list_positions()[0]
    assert position.shares == 5
    assert round(position.total_cost, 2) == 605.0
    assert round(position.avg_entry_price, 2) == 121.0

    marked = repository.mark_portfolio(price_map={"RELIANCE": 125.0}, mark_date=date(2026, 3, 5))
    assert round(marked.total_market_value, 2) == 625.0
    assert round(marked.total_unrealized_pnl, 2) == 20.0
    assert marked.priced_positions == 1
    assert marked.unpriced_positions == 0

    daily_mark = repository.list_daily_marks(limit=1)[0]
    assert round(daily_mark.realized_pnl, 2) == 320.0
    assert round(daily_mark.total_realized_pnl, 2) == 320.0
    assert round(daily_mark.unrealized_pnl, 2) == 20.0


class FakeMarketData:
    def history(self, ticker: str, period: str = "max", interval: str = "1d") -> pd.DataFrame:
        _ = period, interval
        index = pd.to_datetime(["2026-03-03", "2026-03-04"])
        if ticker == "RELIANCE.NS":
            return pd.DataFrame({"Close": [105.0, 115.0]}, index=index)
        return pd.DataFrame()

    def load_price_data(self, ticker: str, period: str = "6mo"):  # pragma: no cover - not used in this test
        raise NotImplementedError


def test_repair_portfolio_history_backfills_daily_marks() -> None:
    repository = build_repository()
    seed_fill(
        repository,
        order_id="order-1",
        run_id="run-1",
        ticker="RELIANCE",
        action="BUY",
        shares=10,
        fill_price=100.0,
        charges=0.0,
        created_at=datetime(2026, 3, 3, 4, 0, tzinfo=UTC),
        metadata={"position_type": "QUALITY"},
    )
    seed_fill(
        repository,
        order_id="order-2",
        run_id="run-2",
        ticker="RELIANCE",
        action="SELL",
        shares=5,
        fill_price=110.0,
        charges=0.0,
        created_at=datetime(2026, 3, 4, 4, 0, tzinfo=UTC),
    )
    with repository.session_factory() as session:
        session.add(
            DailyMark(
                mark_date=date(2026, 3, 3),
                portfolio_value=0.0,
                cash_balance=0.0,
                realized_pnl=0.0,
                total_realized_pnl=0.0,
                unrealized_pnl=0.0,
                benchmark_close=22_000.0,
                benchmark_return_pct=0.5,
                alpha_pct=None,
                details={},
            )
        )
        session.add(
            DailyMark(
                mark_date=date(2026, 3, 4),
                portfolio_value=0.0,
                cash_balance=0.0,
                realized_pnl=0.0,
                total_realized_pnl=0.0,
                unrealized_pnl=0.0,
                benchmark_close=22_100.0,
                benchmark_return_pct=1.0,
                alpha_pct=None,
                details={},
            )
        )
        session.commit()

    orchestrator = Orchestrator(repository=repository, agents={}, boss=object(), market_data=FakeMarketData())
    result = orchestrator.repair_portfolio_history()
    assert result["marks_repaired"] == 2

    marks = repository.list_daily_marks(limit=5)
    latest = marks[0]
    earlier = marks[1]
    assert round(earlier.portfolio_value, 2) == 1_000_050.0
    assert round(earlier.unrealized_pnl, 2) == 50.0
    assert round(latest.portfolio_value, 2) == 1_000_125.0
    assert round(latest.realized_pnl, 2) == 50.0
    assert round(latest.total_realized_pnl, 2) == 50.0
    assert round(latest.unrealized_pnl, 2) == 75.0
    assert latest.details["total_return_pct"] == pytest.approx(0.0125)
