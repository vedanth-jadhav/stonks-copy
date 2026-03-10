from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from quant_trading.tools.screener_client import ScreenerClient, ScreenerClientError


class _Completed:
    def __init__(self, payload: dict, returncode: int = 0, stderr: str = "") -> None:
        self.stdout = json.dumps(payload)
        self.returncode = returncode
        self.stderr = stderr


def test_fetch_batch_normalizes_envelope_and_uses_real_cli_flags(monkeypatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def fake_run(command, cwd, check, capture_output, text, timeout):  # noqa: ANN001
        seen.append(command)
        assert cwd == tmp_path
        assert check is False
        assert capture_output is True
        assert text is True
        assert timeout == 15
        return _Completed(
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "input": "https://www.screener.in/screens/1/test/",
                            "success": True,
                            "source": "live",
                            "cache_hit": False,
                            "data": {"symbol": "TCS", "name": "TCS", "top_ratios": {"ROCE": 25}},
                        }
                    ],
                    "total": 1,
                    "failed": 0,
                },
                "meta": {"command": "fetch batch", "source": "live", "cache_hit": False},
                "error": None,
            }
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = ScreenerClient(command="screener", working_directory=tmp_path, timeout_seconds=15, retries=0)
    payload = client.fetch_batch(
        ["https://www.screener.in/screens/1/test/"],
        fields="top_ratios,tables,investors",
        view="consolidated",
        since="24h",
        concurrency=4,
    )

    assert payload["success"] is True
    assert payload["total"] == 1
    assert payload["failed"] == 0
    assert payload["items"][0]["data"]["symbol"] == "TCS"
    assert payload["items"][0]["success"] is True
    assert seen[0] == [
        "screener",
        "--no-interactive",
        "--output",
        "json",
        "--i-understand",
        "fetch",
        "batch",
        "--fields",
        "top_ratios,tables,investors",
        "--view",
        "consolidated",
        "--url",
        "https://www.screener.in/screens/1/test/",
        "--since",
        "24h",
        "--concurrency",
        "4",
    ]


def test_fetch_company_extracts_company_from_envelope(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, cwd, check, capture_output, text, timeout):  # noqa: ANN001
        assert command[-5:] == ["TCS", "--fields", "all", "--view", "auto"]
        return _Completed(
            {
                "success": True,
                "data": {
                    "symbol": "TCS",
                    "name": "Tata Consultancy Services",
                    "top_ratios": {"ROE": 42},
                },
                "meta": {"command": "fetch company", "source": "cache", "cache_hit": True},
                "error": None,
            }
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = ScreenerClient(command="screener", working_directory=tmp_path, retries=0)
    payload = client.fetch_company("TCS")

    assert payload["symbol"] == "TCS"
    assert payload["name"] == "Tata Consultancy Services"


def test_fetch_query_uses_query_subcommand(monkeypatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def fake_run(command, cwd, check, capture_output, text, timeout):  # noqa: ANN001
        seen.append(command)
        assert cwd == tmp_path
        return _Completed(
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "input": "market_cap >= 500 AND market_cap <= 50000",
                            "success": True,
                            "data": {"symbol": "INFY"},
                        }
                    ],
                    "total": 1,
                    "failed": 0,
                },
                "meta": {"command": "fetch query"},
                "error": None,
            }
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = ScreenerClient(command="screener", working_directory=tmp_path, retries=0)
    payload = client.fetch_query("market_cap >= 500 AND market_cap <= 50000", fields="top_ratios", view="consolidated")

    assert payload["items"][0]["data"]["symbol"] == "INFY"
    assert seen[0] == [
        "screener",
        "--no-interactive",
        "--output",
        "json",
        "--i-understand",
        "fetch",
        "query",
        "market_cap >= 500 AND market_cap <= 50000",
        "--fields",
        "top_ratios",
        "--view",
        "consolidated",
    ]


def test_fetch_batch_raises_on_error_envelope(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, cwd, check, capture_output, text, timeout):  # noqa: ANN001
        _ = command, cwd, check, capture_output, text, timeout
        return _Completed(
            {
                "success": False,
                "data": None,
                "error": {"message": "auth required"},
                "meta": {"command": "fetch batch"},
            },
            returncode=1,
            stderr="auth required",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = ScreenerClient(command="screener", working_directory=tmp_path, retries=0)

    with pytest.raises(ScreenerClientError, match="auth required"):
        client.fetch_batch(["https://www.screener.in/screens/1/test/"])
