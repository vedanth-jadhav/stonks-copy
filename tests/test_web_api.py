from __future__ import annotations

import time
from importlib import import_module
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from quant_trading.config import get_settings


def build_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'control-room.db'}")
    monkeypatch.setenv("WEB_PASSWORD", "test-pass")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("CLIPROXY_AUTH_DIR", str(tmp_path / "cliproxy-auth"))
    monkeypatch.setenv("WEB_STATIC_DIR", str(tmp_path / "frontend-dist"))
    get_settings.cache_clear()
    module = import_module("quant_trading.web.app")
    app = module.create_app()
    return TestClient(app)


def login(client: TestClient) -> str:
    response = client.post("/api/session/login", json={"password": "test-pass"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    return str(payload["csrf_token"])


def test_overview_requires_login(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    response = client.get("/api/overview")
    assert response.status_code == 401


def test_web_settings_default_to_warning_log_level(monkeypatch, tmp_path) -> None:
    _ = tmp_path
    monkeypatch.delenv("WEB_LOG_LEVEL", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.web.log_level == "warning"


def test_pause_and_resume_require_csrf(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    csrf_token = login(client)

    forbidden = client.post("/api/control/pause", json={"reason": "Need to inspect"})
    assert forbidden.status_code == 403

    paused = client.post("/api/control/pause", json={"reason": "Need to inspect"}, headers={"x-csrf-token": csrf_token})
    assert paused.status_code == 200
    assert paused.json()["autonomy_paused"] is True

    resumed = client.post("/api/control/resume", json={"reason": "Resume trading"}, headers={"x-csrf-token": csrf_token})
    assert resumed.status_code == 200
    assert resumed.json()["autonomy_paused"] is False


def test_run_now_enqueues_job_request(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    csrf_token = login(client)

    queued = client.post("/api/control/jobs/pipeline/run-now", headers={"x-csrf-token": csrf_token})
    assert queued.status_code == 202
    payload = queued.json()
    assert payload["job_name"] == "pipeline"
    assert payload["status"] == "queued"

    requests = client.get("/api/control/job-requests")
    assert requests.status_code == 200
    assert requests.json()[0]["id"] == payload["request_id"]


def test_desk_message_and_websocket_snapshot(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    csrf_token = login(client)

    created = client.post(
        "/api/control/desk-messages",
        json={"raw_text": "ban RELIANCE for now", "scope": "global"},
        headers={"x-csrf-token": csrf_token},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["parsed_intent"]["kind"] == "ban_ticker"

    listed = client.get("/api/desk-messages?active_only=true")
    assert listed.status_code == 200
    assert listed.json()[0]["raw_text"] == "ban RELIANCE for now"

    with client.websocket_connect("/ws/control-room") as websocket:
        first_message = websocket.receive_json()
        assert first_message["type"] == "snapshot.init"
        assert "portfolio" in first_message["payload"]


def test_system_map_and_artifact_routes(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    login(client)

    logs_dir = tmp_path / "logs"
    reports_dir = tmp_path / "reports"
    data_dir = tmp_path / "data"
    logs_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    (logs_dir / "pipeline_test.log").write_text("pipeline ok", encoding="utf-8")
    (reports_dir / "week_test.md").write_text("# weekly", encoding="utf-8")
    (data_dir / "validated_pairs.json").write_text('{"pairs":["RELIANCE-INFY"]}', encoding="utf-8")

    system_map = client.get("/api/system-map")
    assert system_map.status_code == 200
    payload = system_map.json()
    assert "top_metrics" in payload
    assert "nodes" in payload
    assert payload["boss"]["label"] == "BOSS"

    logs = client.get("/api/logs")
    assert logs.status_code == 200
    assert any(item["relative_path"] == "pipeline_test.log" for item in logs.json())

    log_detail = client.get("/api/logs/pipeline_test.log")
    assert log_detail.status_code == 200
    assert "pipeline ok" in log_detail.json()["preview"]

    reports = client.get("/api/reports")
    assert reports.status_code == 200
    assert any(item["relative_path"] == "week_test.md" for item in reports.json())

    config_files = client.get("/api/config-files")
    assert config_files.status_code == 200
    assert any(item["relative_path"] == "validated_pairs.json" for item in config_files.json())


def test_gemini_oauth_routes(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    csrf_token = login(client)

    auth_dir = tmp_path / "cliproxy-auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    binary_path = tmp_path / "cli-proxy-api"
    binary_path.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "sleep 1",
                f"cat <<'EOF' > '{auth_dir / 'gemini-operator@example.com-demo-project.json'}'",
                "{",
                '  "type": "gemini",',
                '  "email": "operator@example.com",',
                '  "project_id": "demo-project",',
                '  "token": {',
                '    "refresh_token": "refresh-token",',
                '    "client_id": "client-id",',
                '    "client_secret": "client-secret",',
                '    "token_uri": "https://oauth2.googleapis.com/token"',
                "  }",
                "}",
                "EOF",
            ]
        ),
        encoding="utf-8",
    )
    binary_path.chmod(0o755)

    module = import_module("quant_trading.web.gemini_oauth")

    def fake_install(self):  # noqa: ANN001, ANN202
        return self.update_settings(str(binary_path)) | {"installed_version": "v-test"}

    monkeypatch.setattr(module.GeminiOAuthManager, "install_cli_proxy", fake_install)

    install_response = client.post("/api/gemini-oauth/install-cli-proxy", headers={"x-csrf-token": csrf_token})
    assert install_response.status_code == 200
    assert install_response.json()["installed_version"] == "v-test"

    settings_response = client.put(
        "/api/gemini-oauth/settings",
        json={"binary_path": str(binary_path), "login_mode": "code_assist", "project_id": "demo-project"},
        headers={"x-csrf-token": csrf_token},
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["binary_exists"] is True
    assert settings_response.json()["default_login_mode"] == "code_assist"
    assert settings_response.json()["default_project_id"] == "demo-project"
    assert settings_response.json()["runtime_source"] == "managed-local"
    assert settings_response.json()["runtime_base_url"] == "http://127.0.0.1:8317"

    start = client.post(
        "/api/gemini-oauth/login/start",
        json={"login_mode": "code_assist", "project_id": "demo-project"},
        headers={"x-csrf-token": csrf_token},
    )
    assert start.status_code == 200
    assert start.json()["status"] == "running"
    assert start.json()["login_mode"] == "code_assist"
    assert start.json()["project_id"] == "demo-project"

    completed = None
    for _ in range(20):
        time.sleep(0.2)
        session = client.get("/api/gemini-oauth/login/session")
        assert session.status_code == 200
        payload = session.json()
        if payload["status"] != "running":
            completed = payload
            break
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["account_id"] == "gemini-operator@example.com-demo-project.json"

    accounts = client.get("/api/gemini-oauth/accounts")
    assert accounts.status_code == 200
    account_payload = accounts.json()
    assert len(account_payload) == 1
    assert account_payload[0]["email"] == "operator@example.com"
    assert account_payload[0]["usage"]["models"][0]["remaining_percent"] is None

    def fake_probe(self, path):  # noqa: ANN001, ANN202
        _ = path
        return {
            "checked_at": "2026-03-07T09:30:00+00:00",
            "error": None,
            "models": {
                "gemini-3.1-pro-preview": {
                    "model_id": "gemini-3.1-pro-preview",
                    "remaining_fraction": 0.75,
                    "remaining_percent": 75.0,
                    "available": True,
                },
                "gemini-3-flash-preview": {
                    "model_id": "gemini-3-flash-preview",
                    "remaining_fraction": 0.4,
                    "remaining_percent": 40.0,
                    "available": True,
                },
            },
        }

    monkeypatch.setattr(module.GeminiOAuthManager, "_probe_usage", fake_probe)

    refreshed = client.post(
        "/api/gemini-oauth/accounts/gemini-operator@example.com-demo-project.json/refresh-usage",
        headers={"x-csrf-token": csrf_token},
    )
    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    assert refreshed_payload["status"] == "ready"
    assert refreshed_payload["usage"]["models"][0]["remaining_percent"] == 75.0

    def fake_probe_error(self, path):  # noqa: ANN001, ANN202
        _ = (self, path)
        request = httpx.Request("POST", "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels")
        response = httpx.Response(403, request=request, text="permission denied to enable service [cloudaicompanion.googleapis.com]")
        raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    monkeypatch.setattr(module.GeminiOAuthManager, "_probe_usage", fake_probe_error)

    refresh_error = client.post(
        "/api/gemini-oauth/accounts/gemini-operator@example.com-demo-project.json/refresh-usage",
        headers={"x-csrf-token": csrf_token},
    )
    assert refresh_error.status_code == 200
    refresh_error_payload = refresh_error.json()
    assert refresh_error_payload["status"] == "unknown"
    assert refresh_error_payload["usage"]["unsupported"] is True
    assert "Remaining quota is not exposed" in refresh_error_payload["usage"]["error"]

    deleted = client.delete(
        "/api/gemini-oauth/accounts/gemini-operator@example.com-demo-project.json",
        headers={"x-csrf-token": csrf_token},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    accounts_after_delete = client.get("/api/gemini-oauth/accounts")
    assert accounts_after_delete.status_code == 200
    assert accounts_after_delete.json() == []
