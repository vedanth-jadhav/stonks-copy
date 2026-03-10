"""
signals.py — Pure-function signal computers for historical backtest.

Each function takes a slice of OHLCV history (as a pd.DataFrame with
Open/High/Low/Close/Volume columns, sorted chronologically) and returns
a float signal in [-1, 1].

These replicate the exact formulas from the live agents in:
  quant_trading/agents/core.py (MomentumAgent, ReversionAgent, LiquidityAgent, SectorAgent)

No imports from agent code — kept standalone to avoid coupling live/sim paths.
"""

from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Sequence

import pandas as pd


# ---------------------------------------------------------------------------
# Private helpers (mirrors _closes, _returns, _ema, _corr, etc. in core.py)
# ---------------------------------------------------------------------------


def _closes(df: pd.DataFrame, lookback: int | None = None) -> list[float]:
    closes = df["Close"].tolist()
    return closes[-lookback:] if lookback else closes


def _returns(closes: Sequence[float]) -> list[float]:
    if len(closes) < 2:
        return []
    return [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes))]


def _ema(values: Sequence[float], span: int) -> float:
    if not values:
        return 0.0
    alpha = 2 / (span + 1)
    ema_val = float(values[0])
    for v in values[1:]:
        ema_val = (alpha * float(v)) + ((1 - alpha) * ema_val)
    return ema_val


def _corr(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    mean_a = mean(a)
    mean_b = mean(b)
    dev_a = [x - mean_a for x in a]
    dev_b = [x - mean_b for x in b]
    denom = math.sqrt(sum(x * x for x in dev_a) * sum(y * y for y in dev_b))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(dev_a, dev_b)) / denom


def _percentile_rank(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda item: item[1])
    if len(ordered) == 1:
        return {ordered[0][0]: 1.0}
    return {ticker: idx / (len(ordered) - 1) for idx, (ticker, _) in enumerate(ordered)}


def _score_to_unit_interval(raw: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (raw - lo) / (hi - lo)))


def _rank_time_series(values: Sequence[float], window: int) -> float:
    if len(values) < window:
        return 0.0
    window_values = list(values[-window:])
    ordered = sorted(window_values)
    latest = window_values[-1]
    rank = ordered.index(latest)
    return rank / max(len(window_values) - 1, 1)


# ---------------------------------------------------------------------------
# Signal computers
# ---------------------------------------------------------------------------


def compute_momentum_score(
    prices: pd.DataFrame,
    nifty_prices: pd.DataFrame,
    vix_close: float,
    regime: str = "NEUTRAL",
) -> float:
    """
    Mirrors MomentumAgent._bundle() from agents/core.py.

    Args:
        prices: OHLCV history for the stock (at least 252 bars, up to date t)
        nifty_prices: ^NSEI OHLCV history (at least 63 bars, up to date t)
        vix_close: ^INDIAVIX daily close on date t
        regime: market regime string ("NEUTRAL", "CAUTION", "BEAR", "CRISIS")

    Returns:
        Raw (un-ranked) momentum score. Callers should cross-sectionally rank.
    """
    closes = _closes(prices)
    if len(closes) < 252:
        return 0.0

    rets = _returns(closes)
    vol = pstdev(rets[-63:]) if len(rets) >= 63 else 0.0
    raw_mom = (closes[-21] / closes[-252]) - 1.0
    mom_adj = raw_mom / vol if vol > 0 else 0.0

    bench_closes = _closes(nifty_prices)
    rs_signal = 0.0
    if len(bench_closes) >= 63:
        rs = (closes[-1] / closes[-63]) / max(bench_closes[-1] / bench_closes[-63], 1e-9)
        rs_signal = 1.0 if rs > 1.10 else (-1.0 if rs < 0.90 else 0.0)

    # alpha1 — uses last 6 bars of open/close/volume
    recent_open = prices["Open"].tolist()[-6:]
    recent_close = prices["Close"].tolist()[-6:]
    recent_volume = prices["Volume"].tolist()[-6:]
    vol_deltas: list[float] = []
    intraday: list[float] = []
    for idx in range(1, len(recent_close)):
        prev_vol = max(float(recent_volume[idx - 1]), 1.0)
        vol_deltas.append(
            math.log(max(float(recent_volume[idx]), 1.0)) - math.log(prev_vol)
        )
        intraday.append(
            (float(recent_close[idx]) - float(recent_open[idx]))
            / max(float(recent_open[idx]), 1e-6)
        )
    alpha1 = -_corr(vol_deltas, intraday)

    highs = prices["High"].tolist()
    lows = prices["Low"].tolist()
    volumes = prices["Volume"].tolist()
    high_52 = max(highs[-252:])
    low_52 = min(lows[-252:])
    proximity = (closes[-1] - low_52) / max(high_52 - low_52, 1e-9)
    adv20 = mean(volumes[-20:]) if len(volumes) >= 20 else 0.0
    breakout = (
        1.0 if proximity > 0.90 and float(volumes[-1]) > (1.5 * adv20) else 0.0
    )

    score = (0.45 * mom_adj) + (0.25 * rs_signal) + (0.15 * alpha1) + (0.15 * breakout)

    if vix_close > 28 or regime == "CRISIS":
        return 0.0
    if vix_close > 20 or regime in {"CAUTION", "BEAR"}:
        score *= 0.5

    return score


def compute_momentum_scores_cross_section(
    tickers: list[str],
    price_map: dict[str, pd.DataFrame],
    nifty_prices: pd.DataFrame,
    vix_close: float,
    regime: str = "NEUTRAL",
) -> dict[str, float]:
    """
    Compute cross-sectionally ranked momentum scores for all tickers.
    Returns {ticker: ranked_score} in [-1, 1].
    """
    raw: dict[str, float] = {}
    for ticker in tickers:
        df = price_map.get(ticker)
        if df is None or len(df) < 252:
            continue
        s = compute_momentum_score(df, nifty_prices, vix_close, regime)
        raw[ticker] = s

    ranked = _percentile_rank(raw)
    return {
        ticker: (
            0.0
            if abs(raw.get(ticker, 0.0)) < 1e-9
            else round((rank * 2) - 1, 4)
        )
        for ticker, rank in ranked.items()
    }


def compute_reversion_score(prices: pd.DataFrame) -> float:
    """
    Mirrors ReversionAgent.evaluate() from agents/core.py.

    Args:
        prices: OHLCV history for the stock (at least 60 bars, up to date t)

    Returns:
        Signal in [-1, 1].
    """
    if len(prices) < 60:
        return 0.0

    closes = _closes(prices, 60)
    ema20 = _ema(closes[-20:], span=20)
    std20 = pstdev(closes[-20:]) if len(closes) >= 20 else 0.0
    z = ((closes[-1] - ema20) / std20) if std20 > 0 else 0.0

    # Bollinger Band compression
    bb_widths: list[float] = []
    for idx in range(20, len(closes) + 1):
        window = closes[idx - 20 : idx]
        sma = mean(window)
        std = pstdev(window) if len(window) > 1 else 0.0
        bb_widths.append(((sma + 2 * std) - (sma - 2 * std)) / max(sma, 1e-9))
    compression = (
        1.0
        if bb_widths and bb_widths[-1] <= sorted(bb_widths)[max(0, int(len(bb_widths) * 0.1) - 1)]
        else 0.0
    )

    lows = prices["Low"].tolist()
    low_rank = 1.0 - _rank_time_series(lows, 9)

    last_open = float(prices["Open"].iloc[-1])
    last_close = float(prices["Close"].iloc[-1])
    last_high = float(prices["High"].iloc[-1])
    last_low = float(prices["Low"].iloc[-1])
    last_volume = float(prices["Volume"].iloc[-1])
    alpha101 = (last_close - last_open) / max((last_high - last_low) + 0.001, 1e-9)
    volumes = prices["Volume"].tolist()
    adv20 = mean(volumes[-20:]) if len(volumes) >= 20 else 0.0
    alpha101 = alpha101 if last_volume > (1.3 * adv20) else 0.0

    entry_zone = -3.5 < z < -2.0
    stop_breach = z <= -3.5
    exit_zone = z > -0.3
    overbought = z > 1.5

    if stop_breach:
        signal = -1.0
    elif entry_zone:
        signal = min(1.0, 0.55 + (0.20 * compression) + (0.15 * low_rank) + (0.10 * max(alpha101, 0.0)))
    elif overbought:
        signal = -0.75
    elif exit_zone:
        signal = -0.30
    else:
        signal = max(
            -0.2,
            min(0.4, (0.10 * compression) + (0.10 * low_rank) + (0.05 * alpha101) - (0.10 * max(z, 0.0))),
        )

    return round(max(-1.0, min(1.0, signal)), 4)


def compute_liquidity_score(prices: pd.DataFrame) -> float:
    """
    Mirrors LiquidityAgent.evaluate() from agents/core.py.

    Args:
        prices: OHLCV history for the stock (at least 21 bars, up to date t)

    Returns:
        Signal in [-1, 1].
    """
    if len(prices) < 21:
        return 0.0

    recent = prices.iloc[-21:]
    closes = recent["Close"].tolist()
    volumes = recent["Volume"].tolist()
    adv_notional = mean(c * v for c, v in zip(closes, volumes))
    adv_cr = adv_notional / 1e7

    rets = _returns(closes)
    illiquidity = (
        mean(
            abs(ret) / max(float(closes[i + 1]) * float(volumes[i + 1]), 1.0)
            for i, ret in enumerate(rets)
        )
        if rets
        else 0.0
    )

    score = (
        0.8 * (_score_to_unit_interval(adv_cr, 25, 500) * 2 - 1)
    ) - (0.2 * _score_to_unit_interval(illiquidity * 1e8, 0, 5))

    return round(max(-1.0, min(1.0, score)), 4)


def compute_sector_multipliers(
    sector_prices: dict[str, pd.DataFrame],
    sector_index_map: dict[str, str],
) -> dict[str, float]:
    """
    Mirrors SectorAgent.evaluate() from agents/core.py.

    Args:
        sector_prices: {sector_etf_ticker: OHLCV DataFrame up to date t}
        sector_index_map: {sector_label: sector_etf_ticker}

    Returns:
        {sector_label: weight_multiplier} where multiplier is 0.5, 1.0, or 1.3.
    """
    sector_scores: dict[str, float] = {}
    for sector_label, etf_ticker in sector_index_map.items():
        df = sector_prices.get(etf_ticker)
        if df is None:
            continue
        closes = _closes(df)
        if len(closes) < 127:
            continue
        r30 = (closes[-1] / closes[-30]) - 1
        r63 = (closes[-1] / closes[-63]) - 1
        r126 = (closes[-1] / closes[-126]) - 1
        sector_scores[sector_label] = (0.2 * r30) + (0.4 * r63) + (0.4 * r126)

    ranks = _percentile_rank(sector_scores)
    return {
        sector: (1.3 if rank > 0.75 else (0.5 if rank < 0.25 else 1.0))
        for sector, rank in ranks.items()
    }


def infer_regime(vix_close: float) -> str:
    """Infer market regime from VIX close (mirrors live system logic)."""
    if vix_close > 28:
        return "CRISIS"
    if vix_close > 24:
        return "BEAR"
    if vix_close > 20:
        return "CAUTION"
    return "NEUTRAL"
