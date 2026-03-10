from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path

from quant_trading.config import Settings, get_settings
from quant_trading.timeutils import market_now


@dataclass(frozen=True, slots=True)
class HolidayCalendarStatus:
    path: Path
    year: int
    ready: bool
    status: str
    fetched_at: datetime | None
    holidays: set[str]
    error: str | None = None


def holiday_cache_path(settings: Settings | None = None, year: int | None = None) -> Path:
    active = settings or get_settings()
    use_year = year or market_now(settings=active).year
    cache_dir = active.holiday_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"nse_holidays_{use_year}.json"


def load_holidays(settings: Settings | None = None, year: int | None = None) -> set[str]:
    return holiday_calendar_status(settings=settings, year=year).holidays


def holiday_calendar_status(
    settings: Settings | None = None,
    year: int | None = None,
    now_utc: datetime | None = None,
) -> HolidayCalendarStatus:
    active_settings = settings or get_settings()
    effective_now = now_utc or datetime.now(UTC)
    # We round to the hour to allow caching while still detecting staleness (32 days)
    cache_key_now = effective_now.replace(minute=0, second=0, microsecond=0)
    use_year = year or market_now(at=effective_now, settings=active_settings).year

    return _cached_holiday_calendar_status(
        holiday_cache_dir=active_settings.holiday_cache_dir,
        year=use_year,
        now_utc=cache_key_now,
    )


@lru_cache(maxsize=4)
def _cached_holiday_calendar_status(
    holiday_cache_dir: Path,
    year: int,
    now_utc: datetime,
) -> HolidayCalendarStatus:
    active_year = year
    effective_now = now_utc

    path = holiday_cache_dir / f"nse_holidays_{active_year}.json"
    if not path.exists():
        return HolidayCalendarStatus(
            path=path,
            year=active_year,
            ready=False,
            status="missing",
            fetched_at=None,
            holidays=set(),
            error="Holiday calendar has not been synced yet.",
        )

    try:
        payload = json.loads(path.read_text())
    except Exception as exc:
        return HolidayCalendarStatus(
            path=path,
            year=active_year,
            ready=False,
            status="invalid",
            fetched_at=None,
            holidays=set(),
            error=str(exc),
        )

    holidays_payload = payload.get("holidays", payload if isinstance(payload, list) else [])
    holidays = {entry["date"] if isinstance(entry, dict) else str(entry) for entry in holidays_payload}
    fetched_at_raw = payload.get("synced_at") or payload.get("fetched_at")
    fetched_at = None
    if isinstance(fetched_at_raw, str):
        try:
            fetched_at = datetime.fromisoformat(fetched_at_raw.replace("Z", "+00:00"))
        except ValueError:
            fetched_at = None

    if payload.get("error"):
        return HolidayCalendarStatus(
            path=path,
            year=active_year,
            ready=False,
            status="error",
            fetched_at=fetched_at,
            holidays=holidays,
            error=str(payload.get("error")),
        )
    if not holidays:
        return HolidayCalendarStatus(
            path=path,
            year=active_year,
            ready=False,
            status="empty",
            fetched_at=fetched_at,
            holidays=set(),
            error="Holiday calendar payload is empty.",
        )
    if fetched_at is None:
        return HolidayCalendarStatus(
            path=path,
            year=active_year,
            ready=False,
            status="unknown_age",
            fetched_at=None,
            holidays=holidays,
            error="Holiday calendar timestamp is missing.",
        )
    if (effective_now - fetched_at).days > 32:
        return HolidayCalendarStatus(
            path=path,
            year=active_year,
            ready=False,
            status="stale",
            fetched_at=fetched_at,
            holidays=holidays,
            error="Holiday calendar is stale.",
        )
    return HolidayCalendarStatus(
        path=path,
        year=active_year,
        ready=True,
        status="ready",
        fetched_at=fetched_at,
        holidays=holidays,
    )



def is_market_day(on_date: date, settings: Settings | None = None) -> bool:
    if on_date.weekday() >= 5:
        return False
    calendar = holiday_calendar_status(settings=settings, year=on_date.year)
    if not calendar.ready:
        return False
    return on_date.isoformat() not in calendar.holidays
