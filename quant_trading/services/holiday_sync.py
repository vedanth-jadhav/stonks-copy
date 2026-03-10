from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx

from quant_trading.config import Settings
from quant_trading.market import holiday_cache_path, load_holidays


DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{2}-[A-Za-z]{3}-\d{4})\b"),
    re.compile(r"\b([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\b"),
]


def _extract_dates(text: str, year: int) -> list[str]:
    values: set[str] = set()
    for pattern in DATE_PATTERNS:
        for raw in pattern.findall(text):
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    parsed = datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
                if parsed.year == year:
                    values.add(parsed.isoformat())
                break
    return sorted(values)


class HolidaySyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def refresh(self, year: int | None = None) -> Path:
        target_year = year or datetime.now(UTC).year
        url = "https://www.nseindia.com/resources/exchange-communication-holidays"
        existing = sorted(load_holidays(self.settings, target_year))
        holidays = existing
        error: str | None = None

        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                "Referer": "https://www.nseindia.com/",
            }
            with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
                holidays = _extract_dates(response.text, target_year) or holidays
        except Exception as exc:  # pragma: no cover - live network path
            error = str(exc)

        payload = {
            "source": url,
            "year": target_year,
            "fetched_at": datetime.now(UTC).isoformat(),
            "holidays": [{"date": holiday} for holiday in holidays],
        }
        if error:
            payload["error"] = error
        path = holiday_cache_path(self.settings, target_year)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        return path

    def refresh_if_stale(self, year: int | None = None, max_age_days: int = 32) -> Path:
        target_year = year or datetime.now(UTC).year
        path = holiday_cache_path(self.settings, target_year)
        if not path.exists():
            return self.refresh(target_year)
        age = datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if age.days >= max_age_days:
            return self.refresh(target_year)
        return path

    def refresh_if_needed(self, now_utc: datetime | None = None) -> Path:
        now = now_utc or datetime.now(UTC)
        target_year = now.year
        path = holiday_cache_path(self.settings, target_year)
        if path.exists():
            try:
                payload = json.loads(path.read_text())
            except Exception:
                payload = {}
            synced_at = payload.get("synced_at") or payload.get("fetched_at")
            if synced_at:
                try:
                    synced_month = datetime.fromisoformat(synced_at.replace("Z", "+00:00")).month
                except ValueError:
                    synced_month = None
                if synced_month == now.month:
                    return path
        return self.refresh_if_stale(year=target_year)
