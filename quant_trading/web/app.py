from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from quant_trading.config import get_settings
from quant_trading.main import build_runtime
from quant_trading.web.auth import SessionData, SessionManager
from quant_trading.web.service import ControlRoomService


class LoginRequest(BaseModel):
    password: str


class DeskMessageRequest(BaseModel):
    raw_text: str
    scope: str = "global"
    expires_in_hours: int | None = Field(default=None, ge=1, le=168)


class RuntimeRequest(BaseModel):
    reason: str = "Operator action"


class ReducePositionRequest(BaseModel):
    fraction: float = Field(default=0.5, ge=0.01, le=1.0)


class GeminiOAuthSettingsRequest(BaseModel):
    binary_path: str | None = None
    login_mode: str | None = None
    project_id: str | None = None


class GeminiOAuthLoginStartRequest(BaseModel):
    login_mode: str | None = None
    project_id: str | None = None


def create_app() -> FastAPI:
    settings = get_settings()
    _, _, orchestrator, _ = build_runtime()
    service = ControlRoomService(orchestrator=orchestrator, settings=settings)
    gemini_oauth = service.gemini_oauth
    auth = SessionManager(secret=settings.web.session_secret)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            gemini_oauth.ensure_runtime_ready()
        except Exception:
            pass
        app.state.control_room = service
        app.state.session_manager = auth
        app.state.settings = settings
        yield

    app = FastAPI(title="Quant Control Room", lifespan=lifespan)

    def require_session(request: Request) -> SessionData:
        return auth.require_request_session(request)

    def require_csrf(request: Request) -> SessionData:
        return auth.verify_csrf(request)

    @app.post("/api/session/login")
    def login(payload: LoginRequest, response: Response) -> dict[str, object]:
        if not auth.verify_password(payload.password, settings.web.password):
            raise HTTPException(status_code=401, detail="Invalid password.")
        session = auth.create_session(response)
        return {"authenticated": True, "csrf_token": session.csrf_token, "subject": session.subject}

    @app.post("/api/login")
    def login_alias(payload: LoginRequest, response: Response) -> dict[str, object]:
        if not auth.verify_password(payload.password, settings.web.password):
            raise HTTPException(status_code=401, detail="Invalid password.")
        session = auth.create_session(response)
        return {"ok": True, "csrf_token": session.csrf_token, "subject": session.subject}

    @app.post("/api/session/logout")
    def logout(response: Response, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        auth.clear_session(response)
        return {"authenticated": False}

    @app.post("/api/logout")
    def logout_alias(response: Response, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        auth.clear_session(response)
        return {"ok": True}

    @app.get("/api/session")
    def session_status(request: Request) -> dict[str, object]:
        session = auth.read_request_session(request)
        if session is None:
            return {"authenticated": False, "csrf_token": None, "subject": None}
        return {"authenticated": True, "csrf_token": session.csrf_token, "subject": session.subject}

    @app.get("/api/overview")
    def overview(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.overview()

    @app.get("/api/system-map")
    def system_map(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.system_map()

    @app.get("/api/health")
    def health(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return {"provider_health": service.provider_health()}

    @app.get("/api/scheduler")
    def scheduler_snapshot(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.scheduler_snapshot()

    @app.get("/api/runs")
    def runs(limit: int = 50, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.runs(limit=limit)

    @app.get("/api/control/job-requests")
    def job_requests(limit: int = 50, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.job_requests(limit=limit)

    @app.get("/api/control/job-requests/{request_id}")
    def job_request_detail(request_id: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        payload = service.job_request_detail(request_id=request_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Job request not found.")
        return payload

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.run_detail(run_id=run_id)

    @app.get("/api/agents")
    def agents(session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.agents()

    @app.get("/api/agents/{agent_id}")
    def agent_detail(agent_id: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.agent_detail(agent_id=agent_id)

    @app.get("/api/agents/{agent_id}/reflections")
    def agent_reflections(agent_id: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        detail = service.agent_detail(agent_id=agent_id)
        return {"agent_id": agent_id, "reflections": detail["reflections"], "ic_snapshot": detail["ic_snapshot"]}

    @app.get("/api/portfolio")
    def portfolio(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.portfolio()

    @app.get("/api/positions")
    def positions(session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.positions()

    @app.get("/api/orders")
    def orders(limit: int = 100, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.orders(limit=limit)

    @app.get("/api/fills")
    def fills(limit: int = 100, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.fills(limit=limit)

    @app.get("/api/decisions")
    def decisions(limit: int = 100, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.decisions(limit=limit)

    @app.get("/api/marks")
    def marks(limit: int = 100, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.marks(limit=limit)

    @app.get("/api/memory")
    def memory_index(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.memory_index()

    @app.get("/api/memory/search")
    def memory_search(q: str | None = None, query: str | None = None, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.memory_search(query=query or q or "")

    @app.get("/api/memory/{ref_id}")
    def memory_detail(ref_id: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        payload = service.memory_detail(ref_id=ref_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Memory node not found.")
        return payload

    @app.get("/api/config")
    def config_snapshot(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.config_snapshot()

    @app.get("/api/gemini-oauth/settings")
    def gemini_oauth_settings(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.gemini_oauth_settings()

    @app.put("/api/gemini-oauth/settings")
    def update_gemini_oauth_settings(
        payload: GeminiOAuthSettingsRequest,
        session: SessionData = Depends(require_csrf),
    ) -> dict[str, object]:
        _ = session
        try:
            return service.update_gemini_oauth_settings(
                binary_path=payload.binary_path,
                login_mode=payload.login_mode,
                project_id=payload.project_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/gemini-oauth/install-cli-proxy")
    def install_gemini_oauth_cli_proxy(session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        try:
            return service.install_gemini_oauth_cli_proxy()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/api/gemini-oauth/accounts")
    def gemini_oauth_accounts(session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.gemini_oauth_accounts()

    @app.post("/api/gemini-oauth/login/start")
    def start_gemini_oauth_login(
        payload: GeminiOAuthLoginStartRequest | None = None,
        session: SessionData = Depends(require_csrf),
    ) -> dict[str, object]:
        _ = session
        try:
            return service.start_gemini_oauth_login(
                login_mode=payload.login_mode if payload else None,
                project_id=payload.project_id if payload else None,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/gemini-oauth/login/session")
    def gemini_oauth_login_session(session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        return service.gemini_oauth_login_session()

    @app.post("/api/gemini-oauth/accounts/{account_id:path}/refresh-usage")
    def refresh_gemini_oauth_usage(account_id: str, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        try:
            return service.refresh_gemini_oauth_usage(account_id=account_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Gemini OAuth account not found.") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.delete("/api/gemini-oauth/accounts/{account_id:path}")
    def delete_gemini_oauth_account(account_id: str, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        try:
            return service.delete_gemini_oauth_account(account_id=account_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Gemini OAuth account not found.") from exc

    @app.get("/api/logs")
    def logs(session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.list_log_files()

    @app.get("/api/logs/{relative_path:path}")
    def log_detail(relative_path: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        try:
            return service.read_log_file(relative_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Log file not found.") from exc

    @app.get("/api/reports")
    def reports(session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.list_report_files()

    @app.get("/api/reports/{relative_path:path}")
    def report_detail(relative_path: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        try:
            return service.read_report_file(relative_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Report not found.") from exc

    @app.get("/api/config-files")
    def config_files(session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.list_config_files()

    @app.get("/api/config-files/{relative_path:path}")
    def config_file_detail(relative_path: str, session: SessionData = Depends(require_session)) -> dict[str, object]:
        _ = session
        try:
            return service.read_config_file(relative_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Config artifact not found.") from exc

    @app.get("/api/desk-messages")
    def desk_messages(active_only: bool = False, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.desk_messages(active_only=active_only)

    @app.get("/api/audit-log")
    def audit_log(limit: int = 50, session: SessionData = Depends(require_session)) -> list[dict[str, object]]:
        _ = session
        return service.operator_actions(limit=limit)

    @app.post("/api/control/pause")
    def pause_runtime(payload: RuntimeRequest, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        return service.pause_autonomy(reason=payload.reason)

    @app.post("/api/control/resume")
    def resume_runtime(payload: RuntimeRequest, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        return service.resume_autonomy(reason=payload.reason)

    @app.post("/api/control/jobs/{job_name}/run-now", status_code=202)
    def run_job_now(job_name: str, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        try:
            return service.run_job_now(job_name=job_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown job '{job_name}'.") from exc

    @app.post("/api/control/desk-messages")
    def create_desk_message(payload: DeskMessageRequest, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        return service.create_desk_message(raw_text=payload.raw_text, scope=payload.scope, expires_in_hours=payload.expires_in_hours)

    @app.post("/api/control/desk-messages/{message_id}/revoke")
    def revoke_desk_message(message_id: str, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        payload = service.revoke_desk_message(message_id=message_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Desk message not found.")
        return payload

    @app.post("/api/control/positions/{ticker}/reduce", status_code=202)
    def reduce_position(ticker: str, payload: ReducePositionRequest, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        try:
            return service.force_exit(ticker=ticker, fraction=payload.fraction)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Position '{ticker}' not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/control/positions/{ticker}/exit", status_code=202)
    def exit_position(ticker: str, session: SessionData = Depends(require_csrf)) -> dict[str, object]:
        _ = session
        try:
            return service.force_exit(ticker=ticker, fraction=1.0)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Position '{ticker}' not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.websocket("/ws/control-room")
    async def control_room_stream(websocket: WebSocket) -> None:
        session = auth.read_websocket_session(websocket)
        if session is None:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        try:
            await websocket.send_json(service.websocket_snapshot())
            while True:
                await asyncio.sleep(settings.web.websocket_refresh_seconds)
                await websocket.send_json({"type": "snapshot.updated", "payload": service.live_snapshot()})
        except WebSocketDisconnect:
            return

    static_dir = settings.project_root / settings.web.static_dir
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        app_dir = static_dir / "_app"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        if app_dir.exists():
            app.mount("/_app", StaticFiles(directory=app_dir), name="app-assets")

        @app.get("/")
        async def frontend_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

        @app.get("/{full_path:path}")
        async def frontend_routes(full_path: str) -> Response:
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                return JSONResponse({"detail": "Not found."}, status_code=404)
            candidate = static_dir / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "quant_trading.web.app:app",
        host=settings.web.host,
        port=settings.web.port,
        reload=False,
        log_level=settings.web.log_level,
        access_log=False,
    )
