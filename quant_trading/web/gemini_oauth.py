from __future__ import annotations

import json
import os
import platform
import socket
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from quant_trading.config import Settings
from quant_trading.tools.cliproxy import CLIProxyConnection


TARGET_MODELS = (
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
)
LOGIN_MODES = {
    "google_one": "Google One",
    "code_assist": "Code Assist",
}

GEMINI_MODELS_ENDPOINT = "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels"
CLIPROXY_RELEASE_API = "https://api.github.com/repos/router-for-me/CLIProxyAPI/releases/latest"
LOCAL_CLIPROXY_BASE_URL = "http://127.0.0.1:8317"
LOCAL_CLIPROXY_HOST = "127.0.0.1"
LOCAL_CLIPROXY_PORT = 8317
LOCAL_CLIPROXY_API_KEY = "quant-control-room-local"
LOGIN_SESSION_TIMEOUT_SECONDS = 300
USAGE_CACHE_TTL_SECONDS = 300
MAX_USAGE_REFRESH_PER_LIST = 3


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


class GeminiOAuthManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.auth_dir = settings.cliproxy.auth_dir.expanduser()
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self._installed_binary_path = settings.data_dir / "bin" / ("cli-proxy-api.exe" if os.name == "nt" else "cli-proxy-api")
        self._config_path = settings.data_dir / "cliproxy" / "config.yaml"
        self._settings_path = settings.data_dir / "cliproxy_ui_settings.json"
        self._usage_cache_path = settings.data_dir / "gemini_oauth_usage_cache.json"
        self._login_session_path = settings.data_dir / "gemini_oauth_login_session.json"
        self._login_lock_path = settings.data_dir / "gemini_oauth_login.lock"
        self._runtime_pid_path = settings.data_dir / "cliproxy" / "runtime.pid"
        self._lock = threading.Lock()
        self._login_session: dict[str, Any] = self._load_login_session()

    def settings_snapshot(self) -> dict[str, Any]:
        saved = self._load_json(self._settings_path)
        configured_binary, effective_binary = self._configured_and_effective_binary(saved)
        default_login_mode = str(saved.get("login_mode") or "google_one").strip()
        if default_login_mode not in LOGIN_MODES:
            default_login_mode = "google_one"
        runtime = self.runtime_status(start_service=False)
        return {
            "binary_path": configured_binary,
            "effective_binary_path": effective_binary,
            "binary_exists": bool(effective_binary and Path(effective_binary).expanduser().exists()),
            "auth_dir": str(self.auth_dir.resolve()),
            "installed_version": saved.get("installed_version"),
            "default_login_mode": default_login_mode,
            "default_project_id": str(saved.get("project_id") or "").strip(),
            "runtime_base_url": runtime["base_url"],
            "runtime_source": runtime["source"],
            "runtime_status": runtime["status"],
        }

    def update_settings(
        self,
        binary_path: str | None,
        *,
        login_mode: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self._load_json(self._settings_path)
        payload["binary_path"] = (binary_path or "").strip()
        if login_mode is not None:
            normalized_mode = str(login_mode).strip() or "google_one"
            if normalized_mode not in LOGIN_MODES:
                raise ValueError(f"Unsupported Gemini login mode '{normalized_mode}'.")
            payload["login_mode"] = normalized_mode
        if project_id is not None:
            payload["project_id"] = str(project_id).strip()
        self._write_json(self._settings_path, payload)
        return self.settings_snapshot()

    def runtime_connection(self, *, start_service: bool = True) -> CLIProxyConnection | None:
        _, binary = self._configured_and_effective_binary()
        if binary:
            binary_path = Path(str(binary)).expanduser()
            if binary_path.exists():
                if start_service:
                    self.ensure_runtime_ready(binary_path)
                return CLIProxyConnection(
                    base_url=LOCAL_CLIPROXY_BASE_URL,
                    api_key=self._runtime_api_key(),
                    source="managed-local",
                )
        env_api_key = str(self.settings.cliproxy.api_key or "").strip()
        env_base_url = str(self.settings.cliproxy.base_url or "").strip()
        if env_api_key and env_base_url:
            return CLIProxyConnection(base_url=env_base_url.rstrip("/"), api_key=env_api_key, source="env")
        return None

    def runtime_status(self, *, start_service: bool = False) -> dict[str, Any]:
        try:
            connection = self.runtime_connection(start_service=start_service)
        except Exception as exc:
            return {"status": "error", "base_url": LOCAL_CLIPROXY_BASE_URL, "source": "managed-local", "error": str(exc)}
        if connection is None:
            return {"status": "disabled", "base_url": None, "source": "disabled"}
        if connection.source == "managed-local":
            healthy = self._local_service_healthy(connection)
            return {
                "status": "ready" if healthy else "starting" if start_service else "configured",
                "base_url": connection.base_url,
                "source": connection.source,
            }
        return {
            "status": "configured",
            "base_url": connection.base_url,
            "source": connection.source,
        }

    def ensure_runtime_ready(self, binary_path: Path | None = None) -> None:
        binary = binary_path
        if binary is None:
            _, configured = self._configured_and_effective_binary()
            if not configured:
                return
            binary = Path(configured).expanduser()
        if not binary.exists():
            return
        connection = CLIProxyConnection(base_url=LOCAL_CLIPROXY_BASE_URL, api_key=self._runtime_api_key(), source="managed-local")
        if self._local_service_healthy(connection):
            return
        self._ensure_cli_proxy_config()
        if not self._acquire_runtime_start_lock():
            return
        try:
            if self._local_service_healthy(connection):
                return
            log_path = self.settings.logs_dir / "cliproxy-runtime.log"
            with log_path.open("a", encoding="utf-8") as handle:
                process = subprocess.Popen(
                    [str(binary), "-config", str(self._config_path)],
                    cwd=self.settings.project_root,
                    stdin=subprocess.DEVNULL,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=True,
                )
            self._write_json(
                self._runtime_pid_path,
                {"pid": process.pid, "started_at": _iso(datetime.now(UTC)), "binary_path": str(binary)},
            )
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if self._local_service_healthy(connection):
                    return
                if process.poll() is not None:
                    raise RuntimeError(f"CLIProxy runtime exited with code {process.returncode}.")
                time.sleep(0.5)
            raise RuntimeError("CLIProxy runtime did not become ready in time.")
        finally:
            self._release_runtime_start_lock()

    def list_accounts(self) -> list[dict[str, Any]]:
        usage_cache = self._load_json(self._usage_cache_path)
        usage_cache, _ = self._refresh_stale_accounts(usage_cache)
        accounts: list[dict[str, Any]] = []
        for path in sorted(self.auth_dir.glob("*.json"), key=lambda item: item.name.lower()):
            account = self._read_account(path)
            if account is None:
                continue
            cached_usage = usage_cache.get(account["account_id"], {})
            account["usage"] = self._normalize_usage(cached_usage)
            account["status"] = self._account_status(account["usage"])
            accounts.append(account)
        return accounts

    def refresh_usage(self, account_id: str) -> dict[str, Any]:
        path = self._resolve_account_path(account_id)
        account = self._read_account(path)
        if account is None:
            raise FileNotFoundError(account_id)
        try:
            usage = self._probe_usage(path)
        except Exception as exc:
            usage = self._usage_failure_payload(exc)
        cache = self._load_json(self._usage_cache_path)
        cache[account_id] = usage
        self._write_json(self._usage_cache_path, cache)
        account["usage"] = self._normalize_usage(usage)
        account["status"] = self._account_status(account["usage"])
        return account

    def delete_account(self, account_id: str) -> dict[str, Any]:
        path = self._resolve_account_path(account_id)
        path.unlink(missing_ok=False)
        cache = self._load_json(self._usage_cache_path)
        cache.pop(account_id, None)
        self._write_json(self._usage_cache_path, cache)
        return {"account_id": account_id, "deleted": True}

    def start_login(self, *, login_mode: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            current_session = self._load_login_session()
            if current_session.get("status") == "running" and not self._login_session_expired(current_session):
                raise RuntimeError("Gemini OAuth login already running.")
            settings = self.settings_snapshot()
            binary = str(settings["effective_binary_path"]).strip()
            if not binary:
                raise FileNotFoundError("CLIProxy binary path is not configured.")
            binary_path = Path(binary).expanduser()
            if not binary_path.exists():
                raise FileNotFoundError(f"CLIProxy binary not found at '{binary_path}'.")
            resolved_mode = str(login_mode or settings["default_login_mode"] or "google_one").strip() or "google_one"
            if resolved_mode not in LOGIN_MODES:
                raise ValueError(f"Unsupported Gemini login mode '{resolved_mode}'.")
            resolved_project_id = str(project_id or settings["default_project_id"] or "").strip()
            if resolved_mode == "code_assist" and not resolved_project_id:
                raise ValueError("Project ID is required for Code Assist login.")
            session_id = uuid.uuid4().hex
            if not self._acquire_login_lock(session_id):
                raise RuntimeError("Gemini OAuth login already running.")
            config_path = self._ensure_cli_proxy_config()
            log_path = self.settings.logs_dir / f"cliproxy-login-{session_id}.log"
            session_payload = {
                "id": session_id,
                "status": "running",
                "started_at": _iso(datetime.now(UTC)),
                "completed_at": None,
                "message": (
                    f"CLIProxy login launched in {LOGIN_MODES[resolved_mode]} mode. "
                    "Finish the browser sign-in to add the account."
                ),
                "binary_path": str(binary_path),
                "account_id": None,
                "login_mode": resolved_mode,
                "project_id": resolved_project_id or None,
                "log_path": str(log_path),
            }
            self._save_login_session(session_payload)
            baseline = self._auth_snapshot()
            thread = threading.Thread(
                target=self._run_login_flow,
                args=(session_id, binary_path, config_path, baseline, resolved_mode, resolved_project_id, log_path),
                daemon=True,
                name="gemini-oauth-login",
            )
            thread.start()
            return dict(session_payload)

    def login_session(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._load_login_session())

    def install_cli_proxy(self) -> dict[str, Any]:
        asset_suffix = self._asset_suffix()
        response = httpx.get(CLIPROXY_RELEASE_API, headers={"Accept": "application/vnd.github+json"}, timeout=30)
        response.raise_for_status()
        release = response.json()
        assets = release.get("assets")
        if not isinstance(assets, list):
            raise RuntimeError("CLIProxy release metadata did not include assets.")
        download_url = ""
        asset_name = ""
        for asset in assets:
            name = str(asset.get("name") or "").strip() if isinstance(asset, dict) else ""
            if name.endswith(asset_suffix):
                asset_name = name
                download_url = str(asset.get("browser_download_url") or "").strip()
                break
        if not download_url:
            raise RuntimeError(f"Could not find a CLIProxy release asset ending in {asset_suffix}.")

        self._installed_binary_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cliproxy-install-") as temp_dir:
            archive_path = Path(temp_dir) / asset_name
            with httpx.stream("GET", download_url, follow_redirects=True, timeout=60) as download:
                download.raise_for_status()
                with archive_path.open("wb") as handle:
                    for chunk in download.iter_bytes():
                        handle.write(chunk)
            extract_dir = Path(temp_dir) / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            if archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path) as bundle:
                    bundle.extractall(extract_dir)
            else:
                with tarfile.open(archive_path, "r:gz") as bundle:
                    bundle.extractall(extract_dir)
            source_binary = extract_dir / ("cli-proxy-api.exe" if os.name == "nt" else "cli-proxy-api")
            if not source_binary.exists():
                raise RuntimeError("CLIProxy archive did not contain the expected executable.")
            shutil.copy2(source_binary, self._installed_binary_path)
        self._installed_binary_path.chmod(0o755)
        self._write_json(
            self._settings_path,
            {
                **self._load_json(self._settings_path),
                "binary_path": str(self._installed_binary_path),
                "installed_version": str(release.get("tag_name") or "").strip() or None,
            },
        )
        snapshot = self.settings_snapshot()
        return snapshot

    def _run_login_flow(
        self,
        session_id: str,
        binary_path: Path,
        config_path: Path,
        baseline: dict[str, int],
        login_mode: str,
        project_id: str,
        log_path: Path,
    ) -> None:
        process: subprocess.Popen[str] | None = None
        try:
            launch_args = [str(binary_path), "-config", str(config_path), "--login"]
            if login_mode == "code_assist" and project_id:
                launch_args.extend(["--project_id", project_id])
            with log_path.open("w", encoding="utf-8") as handle:
                process = subprocess.Popen(
                    launch_args,
                    cwd=self.settings.project_root,
                    stdin=subprocess.PIPE,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if process.stdin is not None:
                    if login_mode == "google_one":
                        process.stdin.write("2\n")
                    process.stdin.close()
                deadline = time.monotonic() + 300
                while time.monotonic() < deadline:
                    account_id = self._detect_new_account(baseline)
                    if account_id:
                        if process.poll() is None:
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.terminate()
                        self._finish_session(
                            session_id,
                            status="completed",
                            message=f"Gemini account '{account_id}' added.",
                            account_id=account_id,
                        )
                        return
                    return_code = process.poll()
                    if return_code is not None:
                        self._finish_session(
                            session_id,
                            status="failed",
                            message=self._login_failure_message(
                                log_path=log_path,
                                return_code=return_code,
                                login_mode=login_mode,
                                project_id=project_id,
                            ),
                        )
                        return
                    time.sleep(1)
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                self._finish_session(session_id, status="timed_out", message="CLIProxy login timed out after 5 minutes.")
        except Exception as exc:  # pragma: no cover - defensive runtime path
            if process and process.poll() is None:
                process.terminate()
            self._finish_session(session_id, status="failed", message=str(exc))

    def _finish_session(self, session_id: str, *, status: str, message: str, account_id: str | None = None) -> None:
        with self._lock:
            session = self._load_login_session()
            if session.get("id") != session_id:
                return
            self._save_login_session(
                {
                    **session,
                    "status": status,
                    "message": message,
                    "account_id": account_id,
                    "completed_at": _iso(datetime.now(UTC)),
                }
            )
            self._release_login_lock(session_id)

    def _load_login_session(self) -> dict[str, Any]:
        payload = self._load_json(self._login_session_path)
        session = {**self._default_session(), **payload}
        self._login_session = session
        return session

    def _save_login_session(self, payload: dict[str, Any]) -> None:
        session = {**self._default_session(), **payload}
        self._write_json(self._login_session_path, session)
        self._login_session = session

    def _login_session_expired(self, payload: dict[str, Any]) -> bool:
        if payload.get("status") != "running":
            return False
        started_at = self._parse_datetime(payload.get("started_at"))
        if started_at is None:
            return True
        return (datetime.now(UTC) - started_at).total_seconds() > LOGIN_SESSION_TIMEOUT_SECONDS

    def _acquire_login_lock(self, session_id: str) -> bool:
        if self._login_lock_path.exists():
            current = self._load_login_session()
            if self._login_session_expired(current):
                self._release_login_lock(str(current.get("id") or ""))
            else:
                return False
        self._login_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self._login_lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(session_id)
        return True

    def _release_login_lock(self, session_id: str) -> None:
        try:
            owner = self._login_lock_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return
        if owner and owner != session_id:
            return
        self._login_lock_path.unlink(missing_ok=True)

    def _acquire_runtime_start_lock(self) -> bool:
        lock_path = self.settings.data_dir / "cliproxy" / "runtime.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if not lock_path.exists():
                    return self._acquire_runtime_start_lock()
                time.sleep(0.2)
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        return True

    def _release_runtime_start_lock(self) -> None:
        lock_path = self.settings.data_dir / "cliproxy" / "runtime.lock"
        lock_path.unlink(missing_ok=True)

    def _local_service_healthy(self, connection: CLIProxyConnection) -> bool:
        if not self._port_open(LOCAL_CLIPROXY_HOST, LOCAL_CLIPROXY_PORT):
            return False
        try:
            response = httpx.get(
                f"{connection.base_url}/v1/models",
                headers={"Authorization": f"Bearer {connection.api_key}"},
                timeout=2,
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    @staticmethod
    def _port_open(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0

    def _refresh_stale_accounts(self, usage_cache: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        refreshed = dict(usage_cache)
        dirty = False
        refresh_count = 0
        for path in sorted(self.auth_dir.glob("*.json"), key=lambda item: item.name.lower()):
            account = self._read_account(path)
            if account is None:
                continue
            cached = refreshed.get(account["account_id"], {})
            if not self._usage_stale(cached):
                continue
            if refresh_count >= MAX_USAGE_REFRESH_PER_LIST:
                break
            try:
                refreshed[account["account_id"]] = self._probe_usage(path)
            except Exception as exc:
                refreshed[account["account_id"]] = self._usage_failure_payload(exc)
            refresh_count += 1
            dirty = True
        if dirty:
            self._write_json(self._usage_cache_path, refreshed)
        return refreshed, dirty

    def _usage_stale(self, payload: dict[str, Any]) -> bool:
        checked_at = self._parse_datetime(payload.get("checked_at"))
        if checked_at is None:
            return True
        return (datetime.now(UTC) - checked_at).total_seconds() > USAGE_CACHE_TTL_SECONDS

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None

    def _runtime_api_key(self) -> str:
        return str(self.settings.cliproxy.api_key or "").strip() or LOCAL_CLIPROXY_API_KEY

    def _configured_and_effective_binary(self, saved: dict[str, Any] | None = None) -> tuple[str, str]:
        payload = saved if saved is not None else self._load_json(self._settings_path)
        configured_binary = str(payload.get("binary_path") or "").strip()
        effective_binary = configured_binary or self._discovered_binary_path()
        return configured_binary, effective_binary

    def _detect_new_account(self, baseline: dict[str, int]) -> str | None:
        for path in sorted(self.auth_dir.glob("*.json"), key=lambda item: item.name.lower()):
            try:
                modified_ns = path.stat().st_mtime_ns
            except FileNotFoundError:
                continue
            if modified_ns <= baseline.get(path.name, -1):
                continue
            account = self._read_account(path)
            if account is not None:
                return account["account_id"]
        return None

    def _auth_snapshot(self) -> dict[str, int]:
        snapshot: dict[str, int] = {}
        for path in self.auth_dir.glob("*.json"):
            try:
                snapshot[path.name] = path.stat().st_mtime_ns
            except FileNotFoundError:
                continue
        return snapshot

    def _resolve_account_path(self, account_id: str) -> Path:
        candidate = (self.auth_dir / account_id).resolve()
        base = self.auth_dir.resolve()
        if candidate != base and base not in candidate.parents:
            raise FileNotFoundError(account_id)
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError(account_id)
        return candidate

    def _read_account(self, path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        account_type = str(payload.get("type") or "").strip().lower()
        if account_type != "gemini" and not path.name.startswith("gemini-"):
            return None
        token = payload.get("token")
        if not isinstance(token, dict):
            return None
        modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        return {
            "account_id": path.name,
            "file_name": path.name,
            "email": str(payload.get("email") or "").strip() or path.stem,
            "project_id": str(payload.get("project_id") or "").strip() or None,
            "modified_at": _iso(modified),
            "size_bytes": path.stat().st_size,
            "has_refresh_token": bool(token.get("refresh_token")),
        }

    def _probe_usage(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        token_payload = payload.get("token")
        if not isinstance(token_payload, dict):
            raise RuntimeError("Gemini auth file is missing token data.")
        access_token = self._refresh_access_token(token_payload)
        response = httpx.post(
            GEMINI_MODELS_ENDPOINT,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "cliproxyapi",
            },
            json={},
            timeout=20,
        )
        response.raise_for_status()
        raw_payload = response.json()
        models = raw_payload.get("models")
        if not isinstance(models, list):
            raise RuntimeError("Gemini quota endpoint returned no model list.")

        normalized: dict[str, Any] = {"checked_at": _iso(datetime.now(UTC)), "models": {}, "error": None}
        for target in TARGET_MODELS:
            normalized["models"][target] = {
                "model_id": target,
                "remaining_fraction": None,
                "remaining_percent": None,
                "available": False,
            }
        for row in models:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").split("/")[-1]
            if name not in TARGET_MODELS:
                continue
            remaining_fraction = row.get("remainingFraction")
            try:
                fraction = float(remaining_fraction)
            except (TypeError, ValueError):
                fraction = None
            normalized["models"][name] = {
                "model_id": name,
                "remaining_fraction": fraction,
                "remaining_percent": None if fraction is None else round(fraction * 100, 1),
                "available": bool(row.get("available", fraction is None or fraction > 0)),
            }
        return normalized

    def _refresh_access_token(self, token_payload: dict[str, Any]) -> str:
        refresh_token = str(token_payload.get("refresh_token") or "").strip()
        if not refresh_token:
            raise RuntimeError("Gemini auth file is missing a refresh token.")
        token_uri = str(token_payload.get("token_uri") or "https://oauth2.googleapis.com/token").strip()
        client_id = str(token_payload.get("client_id") or "").strip()
        client_secret = str(token_payload.get("client_secret") or "").strip()
        response = httpx.post(
            token_uri,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        response.raise_for_status()
        access_token = str(response.json().get("access_token") or "").strip()
        if not access_token:
            raise RuntimeError("Token refresh did not return an access token.")
        return access_token

    def _normalize_usage(self, payload: dict[str, Any]) -> dict[str, Any]:
        checked_at = payload.get("checked_at")
        models = payload.get("models") if isinstance(payload.get("models"), dict) else {}
        unsupported = bool(payload.get("unsupported"))
        normalized_models: list[dict[str, Any]] = []
        for model_id in TARGET_MODELS:
            row = models.get(model_id, {})
            remaining_fraction = row.get("remaining_fraction")
            remaining_percent = row.get("remaining_percent")
            try:
                fraction = None if remaining_fraction is None else float(remaining_fraction)
            except (TypeError, ValueError):
                fraction = None
            try:
                percent = None if remaining_percent is None else float(remaining_percent)
            except (TypeError, ValueError):
                percent = None
            normalized_models.append(
                {
                    "model_id": model_id,
                    "remaining_fraction": fraction,
                    "remaining_percent": percent,
                    "available": bool(row.get("available", fraction is None or fraction > 0)),
                }
            )
        return {
            "checked_at": checked_at,
            "error": payload.get("error"),
            "unsupported": unsupported,
            "models": normalized_models,
        }

    def _account_status(self, usage: dict[str, Any]) -> str:
        if usage.get("error") and not usage.get("unsupported"):
            return "auth-error"
        percents = [row.get("remaining_percent") for row in usage.get("models", [])]
        numeric = [float(value) for value in percents if isinstance(value, (int, float))]
        if not numeric:
            return "unknown"
        if max(numeric) <= 0:
            return "exhausted"
        if min(numeric) <= 0:
            return "warning"
        return "ready"

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True))
            temp_path = Path(handle.name)
        temp_path.replace(path)

    @staticmethod
    def _default_session() -> dict[str, Any]:
        return {
            "id": None,
            "status": "idle",
            "started_at": None,
            "completed_at": None,
            "message": "No Gemini OAuth login in progress.",
            "binary_path": None,
            "account_id": None,
            "login_mode": "google_one",
            "project_id": None,
            "log_path": None,
        }

    def _login_failure_message(self, *, log_path: Path, return_code: int, login_mode: str, project_id: str) -> str:
        tail = self._tail_log(log_path).lower()
        if "project selection required" in tail:
            return (
                "Google One could not auto-discover a project for this account. "
                "Use Code Assist mode and enter a project ID."
            )
        if "failed to get project list" in tail:
            return "CLIProxy could not fetch Google Cloud projects for this account."
        if "no project selected" in tail:
            return "CLIProxy login stopped because no Google Cloud project was selected."
        if "authentication failed" in tail:
            return "Browser authentication did not complete successfully."
        if "project activation required" in tail and "permission denied to enable service [cloudaicompanion.googleapis.com]" in tail:
            target = f" for project {project_id}" if project_id else ""
            return (
                "Gemini login reached Google Cloud onboarding, but this account does not have permission "
                f"to enable Cloud AI Companion{target}. Pick a different project or use an account with project admin access."
            )
        if "cloud ai api is not enabled" in tail:
            target = f" for project {project_id}" if project_id else ""
            return f"Cloud AI API is not enabled{target}."
        if return_code == 0:
            return "CLIProxy login exited without creating a new Gemini auth file."
        return f"CLIProxy login exited with code {return_code}."

    @staticmethod
    def _usage_failure_payload(exc: Exception) -> dict[str, Any]:
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code == 403:
                return {
                    "checked_at": _iso(datetime.now(UTC)),
                    "error": "Remaining quota is not exposed for this Gemini CLI OAuth account. Routing can still work even when usage details are unavailable.",
                    "unsupported": True,
                    "models": {},
                }
            if status_code == 401:
                return {
                    "checked_at": _iso(datetime.now(UTC)),
                    "error": "Google rejected the saved OAuth credentials. Re-authenticate this account.",
                    "unsupported": False,
                    "models": {},
                }
            return {
                "checked_at": _iso(datetime.now(UTC)),
                "error": f"Google quota lookup failed with HTTP {status_code}.",
                "unsupported": False,
                "models": {},
            }
        return {
            "checked_at": _iso(datetime.now(UTC)),
            "error": str(exc) or exc.__class__.__name__,
            "unsupported": False,
            "models": {},
        }

    @staticmethod
    def _tail_log(path: Path, limit: int = 4096) -> str:
        try:
            return path.read_text(encoding="utf-8")[-limit:]
        except OSError:
            return ""

    def _discovered_binary_path(self) -> str:
        if self._installed_binary_path.exists():
            return str(self._installed_binary_path)
        resolved = shutil.which("cli-proxy-api")
        return resolved or ""

    def _ensure_cli_proxy_config(self) -> Path:
        api_key = self._runtime_api_key()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        escaped_auth_dir = str(self.auth_dir.resolve()).replace("'", "''")
        escaped_api_key = api_key.replace("'", "''")
        self._config_path.write_text(
            "\n".join(
                [
                    f'host: "{LOCAL_CLIPROXY_HOST}"',
                    f"port: {LOCAL_CLIPROXY_PORT}",
                    f"auth-dir: '{escaped_auth_dir}'",
                    "api-keys:",
                    f"  - '{escaped_api_key}'",
                    "debug: false",
                    "quota-exceeded:",
                    "  switch-project: true",
                    "  switch-preview-model: true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return self._config_path

    @staticmethod
    def _asset_suffix() -> str:
        system = platform.system().lower()
        machine = platform.machine().lower()
        os_name = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(system)
        arch_name = {
            "arm64": "arm64",
            "aarch64": "arm64",
            "amd64": "amd64",
            "x86_64": "amd64",
        }.get(machine)
        if not os_name or not arch_name:
            raise RuntimeError(f"Unsupported platform for CLIProxy install: {system}/{machine}")
        extension = "zip" if os_name == "windows" else "tar.gz"
        return f"_{os_name}_{arch_name}.{extension}"
