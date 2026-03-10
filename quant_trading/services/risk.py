from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from quant_trading.schemas import PriceData


def closes(price: PriceData, lookback: int | None = None) -> list[float]:
    history = price.history[-lookback:] if lookback else price.history
    return [bar.close for bar in history]


def returns(series: list[float]) -> list[float]:
    if len(series) < 2:
        return []
    return [(series[idx] / series[idx - 1]) - 1.0 for idx in range(1, len(series))]


def beta(asset_returns: list[float], benchmark_returns: list[float]) -> float:
    length = min(len(asset_returns), len(benchmark_returns))
    if length < 3:
        return 0.0
    a = asset_returns[-length:]
    b = benchmark_returns[-length:]
    mean_a = mean(a)
    mean_b = mean(b)
    var_b = sum((value - mean_b) ** 2 for value in b)
    if var_b == 0:
        return 0.0
    cov = sum((av - mean_a) * (bv - mean_b) for av, bv in zip(a, b))
    return cov / var_b


def max_drawdown(series: list[float]) -> float:
    if not series:
        return 0.0
    peak = series[0]
    worst = 0.0
    for value in series:
        peak = max(peak, value)
        if peak <= 0:
            continue
        drawdown = (value / peak) - 1.0
        worst = min(worst, drawdown)
    return abs(worst)


def stop_breaches(positions: list[Any], price_bundle: dict[str, PriceData]) -> list[dict[str, float | str]]:
    breaches: list[dict[str, float | str]] = []
    for position in positions:
        price = price_bundle.get(position.ticker)
        if price is None:
            continue
        last_price = price.last_price or (price.history[-1].close if price.history else None)
        if last_price is None:
            continue
        if position.stop_loss_price is not None and last_price <= position.stop_loss_price:
            breaches.append({"ticker": position.ticker, "breach": "hard_stop", "last_price": last_price})
            continue
        if position.trailing_stop_price is not None and last_price <= position.trailing_stop_price:
            breaches.append({"ticker": position.ticker, "breach": "trailing_stop", "last_price": last_price})
    return breaches


def compute_market_regime(vix: float | None) -> str:
    if vix is None:
        return "NEUTRAL"
    if vix < 14:
        return "BULL"
    if vix < 20:
        return "NEUTRAL"
    if vix < 28:
        return "CAUTION"
    if vix < 35:
        return "BEAR"
    return "CRISIS"


def compute_risk_metrics(
    price_bundle: dict[str, PriceData],
    positions: list[Any],
    benchmark_ticker: str = "^NSEI",
) -> dict[str, Any]:
    benchmark = price_bundle.get(benchmark_ticker)
    benchmark_returns = returns(closes(benchmark, 64)) if benchmark is not None else []
    portfolio_vol_inputs: list[float] = []
    weighted_beta = 0.0
    total_weight = 0.0
    worst_drawdown = 0.0

    for position in positions:
        price = price_bundle.get(position.ticker)
        if price is None:
            continue
        asset_closes = closes(price, 126)
        asset_returns = returns(asset_closes[-64:])
        if asset_returns:
            portfolio_vol_inputs.append(pstdev(asset_returns))
        if benchmark_returns and asset_returns:
            weight = max(position.total_cost, 0.0)
            weighted_beta += beta(asset_returns, benchmark_returns) * weight
            total_weight += weight
        worst_drawdown = max(worst_drawdown, max_drawdown(asset_closes))

    portfolio_vol = mean(portfolio_vol_inputs) if portfolio_vol_inputs else 0.0
    var_95_pct = portfolio_vol * 1.645
    portfolio_beta = (weighted_beta / total_weight) if total_weight > 0 else 0.0
    breaches = stop_breaches(positions, price_bundle)
    return {
        "portfolio_beta": round(portfolio_beta, 4),
        "var_95_pct": round(var_95_pct, 4),
        "mdd_current_pct": round(worst_drawdown, 4),
        "stop_breaches": breaches,
    }
