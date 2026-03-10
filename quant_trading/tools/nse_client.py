from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from quant_trading.timeutils import market_now, market_today

logger = logging.getLogger(__name__)


class NSEClient:
    def __init__(self) -> None:
        try:
            from nse import NSE  # type: ignore
        except ImportError:
            self._client = None
        else:
            try:
                self._client = NSE(download_folder=tempfile.gettempdir())
            except Exception as exc:
                logger.warning("NSEClient init failed: %s: %s", type(exc).__name__, exc)
                self._client = None
        self._cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def provider_health(self) -> dict[str, Any]:
        if self._client is None:
            return {
                "status": "missing_dependency",
                "dependency": "nse",
            }
        try:
            _ = self._client.status()
            status = "ready"
        except Exception as exc:
            return {
                "status": "degraded",
                "dependency": "nse",
                "probe": "status",
                "error": type(exc).__name__,
                "detail": str(exc),
            }
        return {
            "status": status,
            "dependency": "nse",
            "probe": "status",
        }

    def _cached_list(
        self,
        name: str,
        cache_date: str,
        loader: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        cache_key = (name, cache_date)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if self._client is None:
            return []
        try:
            payload = loader()
        except RuntimeError:
            # nse package raises RuntimeError when a date range has no records
            payload = []
        except Exception as exc:
            logger.warning("NSEClient %s failed: %s: %s", name, type(exc).__name__, exc)
            return []
        normalized = payload if isinstance(payload, list) else []
        self._cache[cache_key] = normalized
        return normalized

    def get_fii_dii_data(self) -> list[dict[str, Any]]:
        # nse package has no FII/DII endpoint
        return []

    def get_corporate_actions(self, symbol: str) -> list[dict[str, Any]]:
        return self._cached_list(
            f"corporate_actions:{symbol}",
            market_today().isoformat(),
            lambda: self._client.actions(symbol=symbol),
        )

    def get_asm_list(self) -> list[dict[str, Any]]:
        # nse package has no ASM list endpoint
        return []

    def get_gsm_list(self) -> list[dict[str, Any]]:
        # nse package has no GSM list endpoint
        return []

    def get_circuit_breaker_list(self) -> list[dict[str, Any]]:
        # nse package has no live circuit breaker endpoint
        return []

    def get_bulk_deals(self, symbol: str | None = None) -> list[dict[str, Any]]:
        # Uses the historical archive endpoint (last 7 IST days) — no live bulk-deal endpoint
        name = f"bulk_deals:{symbol or 'all'}"
        now = market_now()
        from_date = now - timedelta(days=7)

        def _load() -> list[dict[str, Any]]:
            records = self._client.bulkdeals("bulk_deals", fromdate=from_date, todate=now)
            if symbol:
                sym_upper = symbol.upper()
                return [r for r in records if r.get("symbol", "").upper() == sym_upper]
            return records

        return self._cached_list(name, market_today().isoformat(), _load)

    def get_block_deals(self, symbol: str | None = None) -> list[dict[str, Any]]:
        name = f"block_deals:{symbol or 'all'}"

        def _load() -> list[dict[str, Any]]:
            result = self._client.blockDeals()
            records: list[dict[str, Any]] = result.get("data", []) if isinstance(result, dict) else []
            if symbol:
                sym_upper = symbol.upper()
                return [r for r in records if r.get("symbol", "").upper() == sym_upper]
            return records

        return self._cached_list(name, market_today().isoformat(), _load)

    def get_latest_circulars(self) -> list[dict[str, Any]]:
        def _load() -> list[dict[str, Any]]:
            result = self._client.circulars()
            if not isinstance(result, dict):
                return []
            records: list[dict[str, Any]] = []
            for value in result.values():
                if isinstance(value, list):
                    records.extend(value)
            return records

        return self._cached_list(
            "latest_circulars",
            market_today().isoformat(),
            _load,
        )
