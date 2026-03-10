from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from math import log
from pathlib import Path
from statistics import mean, pstdev

from quant_trading.tools.yfinance_client import YFinanceClient


DEFAULT_PAIR_CANDIDATES = [
    ("HDFCBANK", "ICICIBANK"),
    ("TCS", "INFY"),
    ("HINDUNILVR", "DABUR"),
    ("COALINDIA", "NTPC"),
    ("ONGC", "BPCL"),
    ("AXISBANK", "KOTAKBANK"),
    ("SUNPHARMA", "DRREDDY"),
]


def _linear_regression_beta_alpha(y: list[float], x: list[float]) -> tuple[float, float]:
    if len(y) != len(x) or len(y) < 3:
        return 1.0, 0.0
    mean_x = mean(x)
    mean_y = mean(y)
    var_x = sum((value - mean_x) ** 2 for value in x)
    if var_x == 0:
        return 1.0, 0.0
    cov_xy = sum((xv - mean_x) * (yv - mean_y) for xv, yv in zip(x, y))
    beta = cov_xy / var_x
    alpha = mean_y - (beta * mean_x)
    return beta, alpha


def _adf_pvalue(spread: list[float]) -> float:
    try:
        from statsmodels.tsa.stattools import adfuller  # type: ignore
    except Exception:
        return 1.0
    try:
        return float(adfuller(spread, autolag="AIC")[1])
    except Exception:
        return 1.0


def _half_life(spread: list[float]) -> float:
    if len(spread) < 20:
        return 0.0
    lagged = spread[:-1]
    delta = [spread[idx] - spread[idx - 1] for idx in range(1, len(spread))]
    beta, _ = _linear_regression_beta_alpha(delta, lagged)
    if beta >= 0:
        return 999.0
    return abs(0.693 / beta)


def load_active_pairs(path: Path, fallback: list[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    return [(row["cheap"], row["rich"]) for row in load_active_pair_rows(path, fallback=fallback)]


def load_active_pair_rows(path: Path, fallback: list[tuple[str, str]] | None = None) -> list[dict[str, float | str | bool]]:
    if not path.exists():
        return [{"cheap": cheap, "rich": rich, "valid": False, "source": "fallback"} for cheap, rich in (fallback or DEFAULT_PAIR_CANDIDATES)]
    payload = json.loads(path.read_text())
    rows = payload.get("pairs", payload if isinstance(payload, list) else [])
    active_pairs: list[dict[str, float | str | bool]] = []
    for row in rows:
        if row.get("valid"):
            active_pairs.append(dict(row))
    if active_pairs:
        return active_pairs
    return [{"cheap": cheap, "rich": rich, "valid": False, "source": "fallback"} for cheap, rich in (fallback or DEFAULT_PAIR_CANDIDATES)]


@dataclass(slots=True)
class PairValidation:
    cheap: str
    rich: str
    beta: float
    alpha: float
    zscore: float
    half_life: float
    adf_pvalue: float
    valid: bool


class PairsService:
    def __init__(
        self,
        output_path: Path,
        market_data: YFinanceClient | None = None,
        candidates: list[tuple[str, str]] | None = None,
    ) -> None:
        self.output_path = output_path
        self.market_data = market_data or YFinanceClient()
        self.candidates = list(candidates or DEFAULT_PAIR_CANDIDATES)

    def revalidate(self) -> list[PairValidation]:
        validations: list[PairValidation] = []
        for cheap, rich in self.candidates:
            cheap_price = self.market_data.load_price_data(f"{cheap}.NS", period="1y")
            rich_price = self.market_data.load_price_data(f"{rich}.NS", period="1y")
            cheap_closes = [bar.close for bar in cheap_price.history[-126:]]
            rich_closes = [bar.close for bar in rich_price.history[-126:]]
            if len(cheap_closes) < 90 or len(rich_closes) < 90:
                validations.append(PairValidation(cheap, rich, 1.0, 0.0, 0.0, 0.0, 1.0, False))
                continue

            log_y = [log(max(value, 1e-6)) for value in cheap_closes]
            log_x = [log(max(value, 1e-6)) for value in rich_closes]
            beta, alpha = _linear_regression_beta_alpha(log_y, log_x)
            spread = [y - ((beta * x) + alpha) for y, x in zip(log_y, log_x)]
            spread_mean = mean(spread)
            spread_std = pstdev(spread) if len(spread) > 1 else 0.0
            zscore = ((spread[-1] - spread_mean) / spread_std) if spread_std > 0 else 0.0
            adf_pvalue = _adf_pvalue(spread[-90:])
            half_life = _half_life(spread[-90:])
            valid = adf_pvalue < 0.05 and 3 <= half_life <= 20
            validations.append(PairValidation(cheap, rich, beta, alpha, zscore, half_life, adf_pvalue, valid))

        payload = {
            "as_of": datetime.now(UTC).isoformat(),
            "pairs": [
                {
                    "cheap": validation.cheap,
                    "rich": validation.rich,
                    "beta": validation.beta,
                    "alpha": validation.alpha,
                    "zscore": validation.zscore,
                    "half_life": validation.half_life,
                    "adf_pvalue": validation.adf_pvalue,
                    "valid": validation.valid,
                }
                for validation in validations
            ],
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2))
        return validations
