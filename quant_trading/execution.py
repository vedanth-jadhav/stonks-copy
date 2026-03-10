from __future__ import annotations

from dataclasses import dataclass

from quant_trading.schemas import PriceData


@dataclass(slots=True)
class ChargeBreakdown:
    stt: float
    exchange_charge: float
    sebi_charge: float
    stamp_duty: float
    gst: float
    dp_charge: float
    total: float


def hlc3_proxy(price: PriceData) -> float:
    if price.previous_bar is not None:
        return (price.previous_bar.high + price.previous_bar.low + price.previous_bar.close) / 3.0
    if price.prev_high is not None and price.prev_low is not None and price.prev_close is not None:
        return (price.prev_high + price.prev_low + price.prev_close) / 3.0
    if price.last_price is not None:
        return price.last_price
    raise ValueError(f"Missing price history for {price.ticker}")


def slippage_pct_from_market_cap(market_cap_cr: float | None) -> float:
    if market_cap_cr is None:
        return 0.003
    if market_cap_cr >= 100_000:
        return 0.0005
    if market_cap_cr >= 20_000:
        return 0.0015
    return 0.003


def compute_delivery_charges(schedule: dict, trade_value: float, action: str) -> ChargeBreakdown:
    stt = trade_value * (schedule["stt_buy"] if action == "BUY" else schedule["stt_sell"])
    exchange_charge = trade_value * (schedule["exchange_buy"] if action == "BUY" else schedule["exchange_sell"])
    sebi_charge = trade_value * (schedule["sebi_buy"] if action == "BUY" else schedule["sebi_sell"])
    stamp_duty = trade_value * schedule["stamp_buy"] if action == "BUY" else 0.0
    gst = (exchange_charge + sebi_charge) * schedule["gst_rate"]
    dp_charge = schedule.get("dp_sell_flat", 0.0) if action == "SELL" else 0.0
    total = stt + exchange_charge + sebi_charge + stamp_duty + gst + dp_charge
    return ChargeBreakdown(
        stt=stt,
        exchange_charge=exchange_charge,
        sebi_charge=sebi_charge,
        stamp_duty=stamp_duty,
        gst=gst,
        dp_charge=dp_charge,
        total=total,
    )


def compute_entry_fill(price: PriceData, market_cap_cr: float | None) -> float:
    base = hlc3_proxy(price)
    return base * (1.0 + slippage_pct_from_market_cap(market_cap_cr))


def compute_exit_fill(price: PriceData, market_cap_cr: float | None, ltp: float | None = None, defensive: bool = False) -> float:
    base = hlc3_proxy(price)
    candidate = min(filter(lambda x: x is not None, [base, ltp])) if defensive and ltp is not None else base
    return candidate * (1.0 - slippage_pct_from_market_cap(market_cap_cr))
