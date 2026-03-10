from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import cycle
import time
from typing import Any

import httpx

from quant_trading.timeutils import market_today


@dataclass(slots=True)
class ExaBudget:
    daily_limit: int
    used: int = 0
    budget_date: date | None = None

    def claim(self) -> bool:
        today = market_today()
        if self.budget_date != today:
            self.budget_date = today
            self.used = 0
        if self.used >= self.daily_limit:
            return False
        self.used += 1
        return True


class ExaClient:
    def __init__(self, api_keys: list[str], base_url: str = "https://api.exa.ai", timeout: float = 20.0) -> None:
        self.api_keys = api_keys
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._budget_by_agent: dict[str, ExaBudget] = {}
        self._keys = cycle(api_keys) if api_keys else None

    def configure_budget(self, agent: str, daily_limit: int) -> None:
        self._budget_by_agent[agent] = ExaBudget(daily_limit=daily_limit)

    def can_query(self, agent: str) -> bool:
        budget = self._budget_by_agent.get(agent)
        return budget.claim() if budget else bool(self.api_keys)

    def search(self, agent: str, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        if not self._keys or not self.can_query(agent):
            return []
        api_key = next(self._keys)
        data: dict[str, Any] | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/search",
                        headers={"x-api-key": api_key},
                        json={"query": query, "numResults": num_results},
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
            except Exception:  # pragma: no cover - network path
                time.sleep(0.5 * (attempt + 1))
        if data is None:
            return []
        return data.get("results", [])
