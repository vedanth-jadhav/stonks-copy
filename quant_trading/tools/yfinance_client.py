from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from quant_trading.types import PriceBar, PriceData


class YFinanceClient:
    def __init__(self, cache_ttl_seconds: float = 15.0) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._price_cache: dict[tuple[str, str], tuple[datetime, PriceData]] = {}

    @staticmethod
    def dependency_available() -> bool:
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            return False
        return yf is not None

    def provider_health(self) -> dict[str, Any]:
        if not self.dependency_available():
            return {
                "status": "missing_dependency",
                "dependency": "yfinance",
            }
        try:
            probe = self.history("^NSEI", period="5d")
        except Exception:
            probe = pd.DataFrame()
        return {
            "status": "ready" if not probe.empty else "degraded",
            "dependency": "yfinance",
            "probe": "^NSEI:5d",
        }

    def history(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        if not self.dependency_available():
            return pd.DataFrame()
        import yfinance as yf  # type: ignore
        return yf.download(tickers=ticker, period=period, interval=interval, progress=False, auto_adjust=False)

    def latest_price(self, ticker: str) -> float | None:
        try:
            import yfinance as yf  # type: ignore
            fast_info = yf.Ticker(ticker).fast_info
            value = fast_info.get("lastPrice") or fast_info.get("last_price")
        except Exception:
            return None
        return float(value) if value is not None else None

    def load_price_data(self, ticker: str, period: str = "6mo") -> PriceData:
        cache_key = (ticker, period)
        cached = self._price_cache.get(cache_key)
        now = datetime.now(UTC)
        if cached is not None:
            cached_at, payload = cached
            if (now - cached_at).total_seconds() <= self.cache_ttl_seconds:
                return payload.model_copy(deep=True)
        frame = self.history(ticker=ticker, period=period)
        bars: list[PriceBar] = []
        if not frame.empty:
            for index, row in frame.tail(252).iterrows():
                when = index.to_pydatetime() if hasattr(index, "to_pydatetime") else datetime.now(UTC)
                bars.append(
                    PriceBar(
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row["Volume"]),
                        as_of=when,
                    )
                )
        previous_bar = bars[-1] if bars else None
        payload = PriceData(
            ticker=ticker,
            last_price=self.latest_price(ticker),
            previous_bar=previous_bar,
            history=bars,
        )
        self._price_cache[cache_key] = (now, payload)
        return payload.model_copy(deep=True)
