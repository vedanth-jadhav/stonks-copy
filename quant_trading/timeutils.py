from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from quant_trading.config import Settings, get_settings


def get_market_tz(settings: Settings | None = None) -> ZoneInfo:
    active = settings or get_settings()
    return ZoneInfo(active.market.timezone)


def market_now(at: datetime | None = None, settings: Settings | None = None) -> datetime:
    candidate = at or datetime.now(UTC)
    if candidate.tzinfo is None:
        candidate = candidate.replace(tzinfo=UTC)
    return candidate.astimezone(get_market_tz(settings))


def market_today(settings: Settings | None = None) -> date:
    return market_now(settings=settings).date()


def market_date_for(moment: datetime, settings: Settings | None = None) -> date:
    return market_now(at=moment, settings=settings).date()
