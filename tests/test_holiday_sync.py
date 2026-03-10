from __future__ import annotations

import json
from datetime import UTC, datetime

from quant_trading.config import Settings
from quant_trading.services.holiday_sync import HolidaySyncService


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        _ = args, kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ = exc_type, exc, tb

    def get(self, url: str, headers: dict[str, str] | None = None) -> FakeResponse:
        _ = url, headers
        return FakeResponse("holiday rows 2026-03-14 and 2026-08-15 and 2025-12-25")


def test_holiday_sync_refresh_parses_and_writes_cache(tmp_path, monkeypatch) -> None:
    import quant_trading.services.holiday_sync as holiday_sync_module

    monkeypatch.setattr(holiday_sync_module.httpx, "Client", FakeClient)
    settings = Settings(data_dir=tmp_path)
    service = HolidaySyncService(settings)
    path = service.refresh(year=2026)

    payload = json.loads(path.read_text())
    assert path.exists()
    assert payload["year"] == 2026
    assert payload["holidays"] == [{"date": "2026-03-14"}, {"date": "2026-08-15"}]


def test_holiday_sync_reuses_current_month_cache(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path)
    service = HolidaySyncService(settings)
    path = tmp_path / "nse_holidays_2026.json"
    path.write_text(
        json.dumps(
            {
                "year": 2026,
                "synced_at": datetime(2026, 3, 2, tzinfo=UTC).isoformat(),
                "holidays": [{"date": "2026-03-14"}],
            }
        )
    )

    cached_path = service.refresh_if_needed(now_utc=datetime(2026, 3, 10, tzinfo=UTC))
    assert cached_path == path
