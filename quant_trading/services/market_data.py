from __future__ import annotations

from bisect import bisect_right
from datetime import UTC, date, datetime
from typing import Any

from quant_trading.config import Settings
from quant_trading.db.repository import QuantRepository
from quant_trading.schemas import PriceData, UniverseItem, PortfolioSnapshot
from quant_trading.tools.yfinance_client import YFinanceClient


class MarketDataService:
    def __init__(self, settings: Settings, repository: QuantRepository, client: YFinanceClient | None = None) -> None:
        self.settings = settings
        self.repository = repository
        self.client = client or YFinanceClient()

    def load_price_bundle(self, universe: list[UniverseItem], existing_bundle: dict[str, PriceData] | None = None) -> dict[str, PriceData]:
        bundle = dict(existing_bundle) if existing_bundle else {}

        # 1. Ensure benchmark and VIX are loaded
        if self.settings.market.benchmark not in bundle:
            bundle[self.settings.market.benchmark] = self.client.load_price_data(self.settings.market.benchmark, period="1y")
        if "^INDIAVIX" not in bundle:
            bundle["^INDIAVIX"] = self.client.load_price_data("^INDIAVIX", period="6mo")

        # 2. Add tickers from universe and positions
        tickers_to_load = {item.ticker for item in universe}
        tickers_to_load.update(position.ticker for position in self.repository.list_positions())

        for ticker in sorted(tickers_to_load):
            if ticker in bundle:
                continue
            symbol = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
            bundle[ticker] = self.client.load_price_data(symbol)
        return bundle

    def get_position_price_map(self, positions: list[Any]) -> dict[str, float]:
        price_map: dict[str, float] = {}
        for position in positions:
            price = self.client.load_price_data(f"{position.ticker}.NS", period="1mo")
            latest = price.last_price or (price.history[-1].close if price.history else None)
            if latest is not None:
                price_map[position.ticker] = latest
        return price_map

    def get_historical_close_series(self, ticker: str) -> list[tuple[date, float]]:
        frame = self.client.history(ticker=ticker, period="max")
        if frame.empty:
            return []
        series: list[tuple[date, float]] = []
        for index, row in frame.iterrows():
            when = index.to_pydatetime() if hasattr(index, "to_pydatetime") else datetime.now(UTC)
            series.append((when.date(), float(row["Close"])))
        return series

    def close_on_or_before(self, series: list[tuple[date, float]], target: date) -> float | None:
        if not series:
            return None
        dates = [item[0] for item in series]
        index = bisect_right(dates, target) - 1
        if index < 0:
            return None
        return series[index][1]

    def get_live_portfolio_snapshot(self) -> PortfolioSnapshot:
        positions = self.repository.list_positions()
        if not positions:
            return self.repository.get_portfolio_snapshot()
        price_map = self.get_position_price_map(positions)
        return self.repository.mark_portfolio(price_map=price_map, persist=False)
