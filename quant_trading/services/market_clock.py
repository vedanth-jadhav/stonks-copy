from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from quant_trading.config import Settings
from quant_trading.market import holiday_calendar_status
from quant_trading.schemas import SessionState


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    timestamp_utc: datetime
    date_local: date
    time_local: time
    session_state: SessionState
    is_market_day: bool
    calendar_ready: bool
    holiday_status: str
    holiday_error: str | None


class MarketClock:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tz = ZoneInfo(settings.market.timezone)

    def snapshot(self, now_utc: datetime | None = None) -> MarketSnapshot:
        now = now_utc or datetime.now(UTC)
        local = now.astimezone(self.tz)
        local_time = local.time().replace(tzinfo=None)
        holiday_status = holiday_calendar_status(self.settings, local.year, now_utc=now)
        holidays = holiday_status.holidays
        is_market_day = holiday_status.ready and local.weekday() < 5 and local.date().isoformat() not in holidays

        pre_open_start = time(9, 0)
        market_open = time(9, 15)
        entry_open = time.fromisoformat(self.settings.market.entry_window_open)
        entry_close = time.fromisoformat(self.settings.market.entry_window_close)
        post_close = time.fromisoformat(self.settings.market.exit_window_close)

        if not is_market_day:
            state = SessionState.CLOSED
        elif local_time < pre_open_start:
            state = SessionState.CLOSED
        elif local_time < market_open:
            state = SessionState.PRE_MARKET
        elif local_time <= entry_close:
            state = SessionState.OPEN
        elif local_time <= post_close:
            state = SessionState.POST_MARKET
        else:
            state = SessionState.CLOSED

        return MarketSnapshot(
            timestamp_utc=now,
            date_local=local.date(),
            time_local=local_time,
            session_state=state,
            is_market_day=is_market_day,
            calendar_ready=holiday_status.ready,
            holiday_status=holiday_status.status,
            holiday_error=holiday_status.error,
        )
