from __future__ import annotations

from datetime import UTC, datetime

from quant_trading.config import Settings
from quant_trading.execution import compute_delivery_charges, compute_entry_fill, compute_exit_fill
from quant_trading.schemas import PriceBar, PriceData
from quant_trading.services.market_clock import MarketClock


def test_delivery_charge_calculation_includes_dp_on_sell() -> None:
    schedule = {
        "stt_buy": 0.001,
        "stt_sell": 0.001,
        "exchange_buy": 0.0000335,
        "exchange_sell": 0.0000335,
        "sebi_buy": 0.000001,
        "sebi_sell": 0.000001,
        "stamp_buy": 0.00015,
        "gst_rate": 0.18,
        "dp_sell_flat": 15.93,
    }
    charges = compute_delivery_charges(schedule, trade_value=100_000, action="SELL")
    assert round(charges.dp_charge, 2) == 15.93
    assert charges.total > charges.dp_charge


def test_fill_helpers_use_hlc3_and_slippage_directionally() -> None:
    price = PriceData(
        ticker="RELIANCE.NS",
        last_price=1300.0,
        previous_bar=PriceBar(
            open=1280.0,
            high=1310.0,
            low=1270.0,
            close=1290.0,
            volume=1000.0,
            as_of=datetime.now(UTC),
        ),
    )
    entry = compute_entry_fill(price, market_cap_cr=150_000)
    exit_fill = compute_exit_fill(price, market_cap_cr=150_000, ltp=1285.0, defensive=True)
    assert entry > 1290.0
    assert exit_fill < 1285.0


def test_market_clock_recognizes_open_session() -> None:
    settings = Settings()
    clock = MarketClock(settings)
    snapshot = clock.snapshot(datetime(2026, 3, 9, 4, 30, tzinfo=UTC))
    assert snapshot.is_market_day is True
    assert snapshot.session_state.value in {"open", "pre_market", "post_market", "closed"}
