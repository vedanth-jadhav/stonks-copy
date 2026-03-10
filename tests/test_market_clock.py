from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quant_trading.config import Settings
from quant_trading.market import holiday_cache_path
from quant_trading.schemas import SessionState
from quant_trading.services.market_clock import MarketClock


def build_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data")


def write_holiday_calendar(settings: Settings, year: int, *, holidays: list[str]) -> None:
    path = holiday_cache_path(settings, year)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"year": %d, "fetched_at": "2026-03-01T00:00:00+00:00", "holidays": [%s]}'
        % (year, ",".join(f'{{"date":"{holiday}"}}' for holiday in holidays)),
        encoding="utf-8",
    )


def test_market_clock_identifies_open_window(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    write_holiday_calendar(settings, 2026, holidays=["2026-01-26"])
    clock = MarketClock(settings)
    snapshot = clock.snapshot(datetime(2026, 3, 6, 4, 30, tzinfo=UTC))  # 10:00 IST
    assert snapshot.is_market_day is True
    assert snapshot.calendar_ready is True
    assert snapshot.session_state == SessionState.OPEN


def test_market_clock_identifies_closed_weekend(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    write_holiday_calendar(settings, 2026, holidays=["2026-01-26"])
    clock = MarketClock(settings)
    snapshot = clock.snapshot(datetime(2026, 3, 7, 4, 30, tzinfo=UTC))  # Saturday
    assert snapshot.is_market_day is False
    assert snapshot.session_state == SessionState.CLOSED


def test_market_clock_fails_closed_when_holiday_calendar_missing(tmp_path: Path) -> None:
    clock = MarketClock(build_settings(tmp_path))
    snapshot = clock.snapshot(datetime(2026, 3, 6, 4, 30, tzinfo=UTC))
    assert snapshot.is_market_day is False
    assert snapshot.calendar_ready is False
    assert snapshot.holiday_status == "missing"
