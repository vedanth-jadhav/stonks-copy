from __future__ import annotations

import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from quant_trading.timeutils import market_today


class ScreenerClientError(RuntimeError):
    """Raised when the local screener CLI returns an unusable response."""


class ScreenerClient:
    def __init__(self, command: str, working_directory: Path, timeout_seconds: int = 30, retries: int = 2) -> None:
        self.command = command
        self.working_directory = working_directory
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self._daily_cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    def _cmd_prefix(self) -> list[str]:
        command_path = Path(self.command)
        if command_path.exists():
            return [str(command_path.resolve())]
        return shlex.split(self.command)

    def _base_command(self) -> list[str]:
        return self._cmd_prefix() + [
            "--no-interactive",
            "--output",
            "json",
            "--i-understand",
        ]

    @staticmethod
    def _normalize_company_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        data = payload.get("data")
        if isinstance(data, dict) and "symbol" in data:
            return data
        if "symbol" in payload:
            return payload
        return {}

    @staticmethod
    def _normalize_batch_payload(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        source = data if isinstance(data, dict) else payload
        items = source.get("items", []) if isinstance(source, dict) else []
        normalized_items: list[dict[str, Any]] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            data_item = item.get("data")
            normalized_items.append(
                {
                    "input": item.get("input"),
                    "success": bool(item.get("success", data_item is not None)),
                    "source": item.get("source") or payload.get("meta", {}).get("source"),
                    "cache_hit": bool(item.get("cache_hit", payload.get("meta", {}).get("cache_hit", False))),
                    "error": item.get("error"),
                    "data": data_item if isinstance(data_item, dict) else {},
                }
            )
        return {
            "success": bool(payload.get("success", True)),
            "items": normalized_items,
            "total": int(source.get("total", len(normalized_items))) if isinstance(source, dict) else len(normalized_items),
            "failed": int(source.get("failed", sum(1 for item in normalized_items if not item["success"])))
            if isinstance(source, dict)
            else sum(1 for item in normalized_items if not item["success"]),
            "meta": payload.get("meta", {}),
            "error": payload.get("error"),
        }

    def _parse_stdout(self, stdout: str) -> dict[str, Any]:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ScreenerClientError("screener CLI returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ScreenerClientError("screener CLI returned a non-object payload")
        return payload

    def _run(self, command: list[str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                raw = subprocess.run(
                    command,
                    cwd=self.working_directory,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                payload = self._parse_stdout(raw.stdout)
                if raw.returncode != 0 or payload.get("success") is False:
                    error = payload.get("error") or {}
                    message = error.get("message") or raw.stderr.strip() or "screener CLI failed"
                    raise ScreenerClientError(message)
                return payload
            except (subprocess.SubprocessError, OSError, ScreenerClientError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(min(2**attempt, 4))
        raise ScreenerClientError(str(last_error) if last_error else "screener CLI failed")

    def fetch_company(
        self,
        symbol_or_url: str,
        *,
        fields: str = "all",
        view: str = "auto",
        since: str | None = None,
    ) -> dict[str, Any]:
        cache_key = ("company", market_today().isoformat(), symbol_or_url, fields, view, since)
        cached = self._daily_cache.get(cache_key)
        if cached is not None:
            return cached
        command = self._base_command() + [
            "fetch",
            "company",
            symbol_or_url,
            "--fields",
            fields,
            "--view",
            view,
        ]
        if since:
            command.extend(["--since", since])
        payload = self._run(command)
        normalized = self._normalize_company_payload(payload)
        self._daily_cache[cache_key] = normalized
        return normalized

    def fetch_batch(
        self,
        screen_urls: list[str],
        *,
        fields: str = "all",
        view: str = "auto",
        since: str | None = None,
        concurrency: int | None = None,
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        if not screen_urls and not symbols:
            return {"success": True, "items": [], "total": 0, "failed": 0, "meta": {}, "error": None}
        normalized_urls = tuple(screen_urls)
        normalized_symbols = tuple(symbol.upper().replace(".NS", "") for symbol in (symbols or []))
        cache_key = ("batch", market_today().isoformat(), normalized_urls, normalized_symbols, fields, view, since, concurrency)
        cached = self._daily_cache.get(cache_key)
        if cached is not None:
            return cached
        command = self._base_command() + [
            "fetch",
            "batch",
            "--fields",
            fields,
            "--view",
            view,
        ]
        if normalized_symbols:
            command.extend(["--symbols", ",".join(normalized_symbols)])
        for url in normalized_urls:
            command.extend(["--url", url])
        if since:
            command.extend(["--since", since])
        if concurrency is not None and concurrency > 0:
            command.extend(["--concurrency", str(concurrency)])
        payload = self._run(command)
        normalized = self._normalize_batch_payload(payload)
        self._daily_cache[cache_key] = normalized
        return normalized

    def fetch_query(
        self,
        query: str,
        *,
        fields: str = "all",
        view: str = "auto",
        since: str | None = None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if not normalized_query:
            return {"success": True, "items": [], "total": 0, "failed": 0, "meta": {}, "error": None}
        cache_key = ("query", market_today().isoformat(), normalized_query, fields, view, since)
        cached = self._daily_cache.get(cache_key)
        if cached is not None:
            return cached
        command = self._base_command() + [
            "fetch",
            "query",
            normalized_query,
            "--fields",
            fields,
            "--view",
            view,
        ]
        if since:
            command.extend(["--since", since])
        payload = self._run(command)
        normalized = self._normalize_batch_payload(payload)
        self._daily_cache[cache_key] = normalized
        return normalized
