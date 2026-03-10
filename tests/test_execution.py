from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from quant_trading.db.repository import QuantRepository
from quant_trading.db.session import create_engine_and_sessionmaker, init_db
from quant_trading.schemas import (
    DecisionType,
    EntryPolicy,
    MarketContext,
    PortfolioSnapshot,
    PositionType,
    PriceBar,
    PriceData,
    SessionState,
    StopPolicy,
    TradeDecision,
)
from quant_trading.services.execution import ExecutionService


def build_repository() -> QuantRepository:
    engine, session_factory = create_engine_and_sessionmaker("sqlite:///:memory:")
    init_db(engine, session_factory)
    return QuantRepository(engine, session_factory)


def build_context(price_data: PriceData) -> MarketContext:
    now = datetime.now(UTC)
    return MarketContext(
        run_id="run-1",
        timestamp_utc=now,
        market="NSE",
        date=now.date(),
        time_ist=time(10, 0),
        session_state=SessionState.OPEN,
        is_market_day=True,
        portfolio=PortfolioSnapshot(cash_balance=1_000_000.0, total_deployed=0.0, portfolio_value=1_000_000.0),
        universe=[],
        price_bundle={"RELIANCE": price_data},
        memory_context={},
        upstream_results={},
    )


def test_delivery_buy_uses_previous_bar_hlc3_and_charges() -> None:
    repository = build_repository()
    service = ExecutionService(repository)
    price_data = PriceData(
        ticker="RELIANCE",
        previous_bar=PriceBar(open=100.0, high=110.0, low=90.0, close=105.0, volume=1_000_000, as_of=datetime.now(UTC)),
        last_price=106.0,
    )
    context = build_context(price_data)
    decision = TradeDecision(
        decision=DecisionType.BUY,
        ticker="RELIANCE",
        position_type=PositionType.QUALITY,
        target_weight=0.05,
        shares=10,
        entry_policy=EntryPolicy(fill_model="prev_session_hlc3"),
        stop_policy=StopPolicy(),
        confidence=0.75,
        reason_code="test",
    )
    result = service.execute(run_id="run-1", context=context, decision=decision)
    assert result is not None
    assert result.fill_price > 100.0
    assert result.charges > 0.0
    assert result.execution_type == "PLANNED_DELIVERY"


def test_defensive_intraday_sell_uses_worse_of_live_and_proxy() -> None:
    repository = build_repository()
    service = ExecutionService(repository)
    seed_price = PriceData(
        ticker="RELIANCE",
        previous_bar=PriceBar(open=99.0, high=101.0, low=98.0, close=100.0, volume=1_000_000, as_of=datetime.now(UTC)),
        last_price=100.0,
    )
    seed_context = build_context(seed_price)
    service.execute(
        run_id="seed-run",
        context=seed_context,
        decision=TradeDecision(
            decision=DecisionType.BUY,
            ticker="RELIANCE",
            position_type=PositionType.QUALITY,
            target_weight=0.05,
            shares=10,
            entry_policy=EntryPolicy(fill_model="prev_session_hlc3"),
            stop_policy=StopPolicy(),
            confidence=0.8,
            reason_code="seed_position",
        ),
    )
    price_data = PriceData(
        ticker="RELIANCE",
        previous_bar=PriceBar(open=100.0, high=120.0, low=90.0, close=110.0, volume=1_000_000, as_of=datetime.now(UTC)),
        last_price=95.0,
    )
    context = build_context(price_data)
    decision = TradeDecision(
        decision=DecisionType.SELL,
        ticker="RELIANCE",
        position_type=PositionType.QUALITY,
        target_weight=0.0,
        shares=10,
        entry_policy=EntryPolicy(fill_model="prev_session_hlc3"),
        stop_policy=StopPolicy(),
        confidence=0.8,
        reason_code="stop_hit",
    )
    result = service.execute(run_id="run-1", context=context, decision=decision)
    assert result is not None
    assert result.execution_type == "DEFENSIVE_INTRADAY"
    assert result.fill_price < 95.0


def test_sell_rejects_oversell_against_fill_ledger() -> None:
    repository = build_repository()
    service = ExecutionService(repository)
    price_data = PriceData(
        ticker="RELIANCE",
        previous_bar=PriceBar(open=99.0, high=101.0, low=98.0, close=100.0, volume=1_000_000, as_of=datetime.now(UTC)),
        last_price=100.0,
    )
    context = build_context(price_data)
    seeded = service.execute(
        run_id="seed-run",
        context=context,
        decision=TradeDecision(
            decision=DecisionType.BUY,
            ticker="RELIANCE",
            position_type=PositionType.QUALITY,
            target_weight=0.05,
            shares=5,
            entry_policy=EntryPolicy(fill_model="prev_session_hlc3"),
            stop_policy=StopPolicy(),
            confidence=0.8,
            reason_code="seed_position",
        ),
    )
    assert seeded is not None

    with pytest.raises(ValueError, match="Unable to sell 6 shares of RELIANCE"):
        service.execute(
            run_id="run-oversell",
            context=context,
            decision=TradeDecision(
                decision=DecisionType.SELL,
                ticker="RELIANCE",
                position_type=PositionType.QUALITY,
                target_weight=0.0,
                shares=6,
                entry_policy=EntryPolicy(fill_model="prev_session_hlc3"),
                stop_policy=StopPolicy(),
                confidence=0.8,
                reason_code="oversell",
            ),
        )


def test_buy_is_blocked_after_entry_window() -> None:
    repository = build_repository()
    service = ExecutionService(repository)
    price_data = PriceData(
        ticker="RELIANCE",
        previous_bar=PriceBar(open=100.0, high=110.0, low=90.0, close=105.0, volume=1_000_000, as_of=datetime.now(UTC)),
        last_price=106.0,
    )
    context = build_context(price_data).model_copy(update={"time_ist": time(15, 5), "session_state": SessionState.POST_MARKET})
    decision = TradeDecision(
        decision=DecisionType.BUY,
        ticker="RELIANCE",
        position_type=PositionType.QUALITY,
        target_weight=0.05,
        shares=10,
        entry_policy=EntryPolicy(fill_model="prev_session_hlc3", valid_until=time(15, 0)),
        stop_policy=StopPolicy(),
        confidence=0.75,
        reason_code="late_entry",
    )
    assert service.execute(run_id="run-late", context=context, decision=decision) is None


def test_sell_is_blocked_after_exit_window() -> None:
    repository = build_repository()
    service = ExecutionService(repository)
    price_data = PriceData(
        ticker="RELIANCE",
        previous_bar=PriceBar(open=100.0, high=110.0, low=90.0, close=105.0, volume=1_000_000, as_of=datetime.now(UTC)),
        last_price=103.0,
    )
    seed_context = build_context(price_data)
    seeded = service.execute(
        run_id="seed-run",
        context=seed_context,
        decision=TradeDecision(
            decision=DecisionType.BUY,
            ticker="RELIANCE",
            position_type=PositionType.QUALITY,
            target_weight=0.05,
            shares=10,
            entry_policy=EntryPolicy(fill_model="prev_session_hlc3", valid_until=time(15, 0)),
            stop_policy=StopPolicy(),
            confidence=0.8,
            reason_code="seed_position",
        ),
    )
    assert seeded is not None
    late_context = seed_context.model_copy(update={"time_ist": time(15, 26), "session_state": SessionState.CLOSED})
    decision = TradeDecision(
        decision=DecisionType.SELL,
        ticker="RELIANCE",
        position_type=PositionType.QUALITY,
        target_weight=0.0,
        shares=10,
        entry_policy=EntryPolicy(fill_model="prev_session_hlc3", valid_until=time(15, 25)),
        stop_policy=StopPolicy(),
        confidence=1.0,
        reason_code="late_exit",
    )
    assert service.execute(run_id="run-late-exit", context=late_context, decision=decision) is None
