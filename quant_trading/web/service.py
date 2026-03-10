from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from quant_trading.config import Settings, settings_dict
from quant_trading.db.models import MemoryEdge, MemoryNode
from quant_trading.jobs import get_job_spec, manual_job_specs, scheduled_job_specs
from quant_trading.market import holiday_cache_path, holiday_calendar_status
from quant_trading.orchestrator import Orchestrator
from quant_trading.tools.nse_client import NSEClient
from quant_trading.web.gemini_oauth import GeminiOAuthManager


AGENT_LAYOUT = {
    "agent_00_discovery": {"label": "Discovery", "stage": "stage_1", "route": "/config"},
    "agent_01_universe": {"label": "Universe", "stage": "stage_1", "route": "/config"},
    "agent_02_quality": {"label": "Quality", "stage": "stage_1", "route": "/config"},
    "agent_03_momentum": {"label": "Momentum", "stage": "stage_2", "route": "/blotter"},
    "agent_04_reversion": {"label": "Reversion", "stage": "stage_2", "route": "/blotter"},
    "agent_05_pairs": {"label": "Pairs", "stage": "stage_2", "route": "/config"},
    "agent_06_macro": {"label": "Macro", "stage": "stage_3", "route": "/config"},
    "agent_07_sector": {"label": "Sector", "stage": "stage_3", "route": "/blotter"},
    "agent_08_ownership": {"label": "Ownership", "stage": "stage_3", "route": "/blotter"},
    "agent_09_sentiment": {"label": "Sentiment", "stage": "stage_3", "route": "/memory"},
    "agent_10_events": {"label": "Events", "stage": "stage_3", "route": "/memory"},
    "agent_11_backtester": {"label": "Backtest", "stage": "stage_4", "route": "/blotter"},
    "agent_12_liquidity": {"label": "Liquidity", "stage": "stage_4", "route": "/portfolio"},
    "agent_13_risk": {"label": "Risk", "stage": "stage_4", "route": "/config"},
    "agent_14_execution": {"label": "Execution", "stage": "stage_5", "route": "/blotter"},
}

STAGE_ORDER = [
    ("stage_1", "Stage 1", "Universe and quality"),
    ("stage_2", "Stage 2", "Signal analysis"),
    ("stage_3", "Stage 3", "Context and macro"),
    ("stage_4", "Stage 4", "Validation and risk"),
    ("stage_5", "Stage 5", "Execution costing"),
]


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=UTC)
        return normalized.astimezone(UTC).isoformat()
    return value


def _redact(value: Any) -> Any:
    if isinstance(value, str) and value:
        return "***"
    if isinstance(value, list):
        return ["***" for _ in value]
    return value


def _sanitize_settings(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    cliproxy = dict(sanitized.get("cliproxy", {}))
    if "api_key" in cliproxy:
        cliproxy["api_key"] = _redact(cliproxy["api_key"])
    sanitized["cliproxy"] = cliproxy

    exa = dict(sanitized.get("exa", {}))
    if "api_keys" in exa:
        exa["api_keys"] = _redact(exa["api_keys"])
    sanitized["exa"] = exa

    web = dict(sanitized.get("web", {}))
    if "password" in web:
        web["password"] = _redact(web["password"])
    if "session_secret" in web:
        web["session_secret"] = _redact(web["session_secret"])
    sanitized["web"] = web
    return sanitized


def _serialize_job(job: Any) -> dict[str, Any]:
    return {
        "id": job.id,
        "name": job.job_name,
        "run_date": job.run_date.isoformat() if job.run_date else None,
        "status": job.status,
        "started_at": _iso(job.started_at),
        "finished_at": _iso(job.finished_at),
        "payload": dict(job.payload or {}),
        "error": job.error,
    }


def _serialize_job_request(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "job_name": row.job_name,
        "dedupe_key": row.dedupe_key,
        "requested_by": row.requested_by,
        "status": row.status,
        "payload": dict(row.payload or {}),
        "result": dict(row.result or {}),
        "error": row.error,
        "run_id": row.run_id,
        "lease_owner": row.lease_owner,
        "lease_expires_at": _iso(row.lease_expires_at),
        "requested_at": _iso(row.requested_at),
        "started_at": _iso(row.started_at),
        "finished_at": _iso(row.finished_at),
    }


def _serialize_agent_run(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "agent_id": row.agent_id,
        "status": row.status,
        "started_at": _iso(row.started_at),
        "finished_at": _iso(row.finished_at),
        "warnings": list(row.warnings or []),
        "artifacts": dict(row.artifacts or {}),
    }


def _serialize_position(row: Any) -> dict[str, Any]:
    return {
        "ticker": row.ticker,
        "shares": row.shares,
        "avg_entry_price": row.avg_entry_price,
        "total_cost": row.total_cost,
        "sector": row.sector,
        "stop_loss_price": row.stop_loss_price,
        "trailing_stop_price": row.trailing_stop_price,
        "position_type": row.position_type,
        "last_updated": _iso(row.last_updated),
    }


def _serialize_order(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "ticker": row.ticker,
        "decision": row.decision,
        "position_type": row.position_type,
        "shares": row.shares,
        "confidence": row.confidence,
        "payload": dict(row.payload or {}),
        "created_at": _iso(row.created_at),
    }


def _serialize_fill(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "order_id": row.order_id,
        "run_id": row.run_id,
        "ticker": row.ticker,
        "action": row.action,
        "shares": row.shares,
        "fill_price": row.fill_price,
        "charges": row.charges,
        "execution_type": row.execution_type,
        "details": dict(row.details or {}),
        "created_at": _iso(row.created_at),
    }


def _serialize_mark(row: Any) -> dict[str, Any]:
    return {
        "mark_date": row.mark_date.isoformat(),
        "portfolio_value": row.portfolio_value,
        "cash_balance": row.cash_balance,
        "realized_pnl": row.realized_pnl,
        "realized_pnl_today": row.realized_pnl,
        "total_realized_pnl": getattr(row, "total_realized_pnl", row.realized_pnl),
        "unrealized_pnl": row.unrealized_pnl,
        "benchmark_close": row.benchmark_close,
        "benchmark_return_pct": row.benchmark_return_pct,
        "alpha_pct": row.alpha_pct,
        "details": dict(row.details or {}),
    }


def _serialize_reflection(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "reflection_date": row.reflection_date.isoformat(),
        "agent_id": row.agent_id,
        "summary": row.summary,
        "lessons": list(row.lessons or []),
    }


def _serialize_decision(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "ticker": row.ticker,
        "decision": row.decision,
        "position_type": row.position_type,
        "shares": row.shares,
        "confidence": row.confidence,
        "origin": row.origin,
        "payload": dict(row.payload or {}),
        "created_at": _iso(row.created_at),
    }


def _serialize_message(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "scope": row.scope,
        "status": row.status,
        "raw_text": row.raw_text,
        "parsed_intent": dict(row.parsed_intent or {}),
        "effective_from": _iso(row.effective_from),
        "expires_at": _iso(row.expires_at),
        "created_at": _iso(row.created_at),
    }


def _serialize_action(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "action": row.action,
        "payload": dict(row.payload or {}),
        "created_at": _iso(row.created_at),
    }


def _severity_rank(value: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(value, 3)


class ControlRoomService:
    def __init__(self, orchestrator: Orchestrator, settings: Settings, gemini_oauth: GeminiOAuthManager | None = None) -> None:
        self.orchestrator = orchestrator
        self.settings = settings
        self.repository = orchestrator.repository
        self.gemini_oauth = gemini_oauth or GeminiOAuthManager(settings=settings)
        self._provider_health_cache: dict[str, Any] | None = None
        self._provider_health_cached_at: datetime | None = None
        self._snapshot_cache: dict[str, tuple[datetime, Any]] = {}

    def _cached(self, key: str, ttl_seconds: float, builder, *, force_refresh: bool = False):
        now = datetime.now(UTC)
        if not force_refresh:
            cached = self._snapshot_cache.get(key)
            if cached is not None:
                cached_at, payload = cached
                if (now - cached_at) <= timedelta(seconds=ttl_seconds):
                    return payload
        payload = builder()
        self._snapshot_cache[key] = (now, payload)
        return payload

    def _invalidate_snapshot_cache(self) -> None:
        self._snapshot_cache.clear()

    def _build_overview(self) -> dict[str, Any]:
        market = self.orchestrator.market_clock.snapshot(datetime.now(UTC))
        portfolio = self.orchestrator.live_portfolio_snapshot().model_dump(mode="json")
        runtime_state = self.repository.sync_entries_blocked_from_desk_messages()
        latest_mark = next(iter(self.repository.list_daily_marks(limit=1)), None)
        latest_jobs = self.repository.list_job_runs(limit=12)
        latest_decisions = self.repository.list_trade_decisions(limit=8)
        latest_actions = self.repository.list_operator_actions(limit=8)
        risk_runs = self.repository.list_agent_runs(limit=1, agent_id="agent_13_risk")
        return {
            "market": {
                "timestamp_utc": market.timestamp_utc.isoformat(),
                "date_local": market.date_local.isoformat(),
                "time_local": market.time_local.isoformat(),
                "session_state": market.session_state,
                "is_market_day": market.is_market_day,
                "calendar_ready": market.calendar_ready,
                "holiday_status": market.holiday_status,
                "holiday_error": market.holiday_error,
            },
            "portfolio": portfolio,
            "runtime_state": {
                **runtime_state,
                "updated_at": _iso(runtime_state.get("updated_at")),
            },
            "latest_mark": _serialize_mark(latest_mark) if latest_mark else None,
            "scheduler": self.scheduler_snapshot(),
            "latest_jobs": [_serialize_job(job) for job in latest_jobs],
            "latest_decisions": [_serialize_decision(row) for row in latest_decisions],
            "latest_actions": [_serialize_action(row) for row in latest_actions],
            "alerts": (risk_runs[0].warnings if risk_runs else []),
            "provider_health": self.provider_health(),
        }

    def overview(self, *, force_refresh: bool = False) -> dict[str, Any]:
        return self._cached("overview", 15.0, self._build_overview, force_refresh=force_refresh)

    def _build_system_map(self, *, overview: dict[str, Any]) -> dict[str, Any]:
        agents = {row["agent_id"]: row for row in self.agents()}
        signals = self.repository.list_signal_history(limit=120)
        signal_counts: dict[str, int] = {}
        for row in signals:
            signal_counts[row.agent_id] = signal_counts.get(row.agent_id, 0) + 1

        nodes: list[dict[str, Any]] = []
        fill_count = len(self.repository.list_fills(limit=25))
        for agent_id, meta in AGENT_LAYOUT.items():
            row = agents.get(agent_id)
            latest_run = row.get("latest_run") if row else None
            ic_snapshot = row.get("ic_snapshot") if row else {}
            warnings = list((latest_run or {}).get("warnings") or [])
            status = "idle"
            if warnings:
                status = "warning"
            if latest_run and latest_run.get("status") == "failed":
                status = "critical"
            elif latest_run and latest_run.get("status") == "succeeded" and not warnings:
                status = "healthy"

            nodes.append(
                {
                    "id": agent_id,
                    "label": meta["label"],
                    "stage": meta["stage"],
                    "route": meta["route"],
                    "status": status,
                    "metric": self._node_metric(
                        agent_id=agent_id,
                        overview=overview,
                        ic_snapshot=ic_snapshot,
                        signal_count=signal_counts.get(agent_id, 0),
                        fill_count=fill_count,
                    ),
                    "updated_at": (latest_run or {}).get("finished_at") or (latest_run or {}).get("started_at"),
                    "warnings": warnings[:2],
                    "summary": self._node_summary(
                        agent_id=agent_id,
                        overview=overview,
                        ic_snapshot=ic_snapshot,
                        signal_count=signal_counts.get(agent_id, 0),
                    ),
                }
            )

        marks = self.repository.list_daily_marks(limit=30)
        latest_mark = marks[0] if marks else None
        ic_snapshot = self.repository.latest_ic_snapshot()
        win_rates = [float(payload["win_rate"]) for payload in ic_snapshot.values() if payload.get("win_rate") is not None]
        provider_health = overview["provider_health"]
        provider_ready = sum(1 for payload in provider_health.values() if payload.get("status") in {"ready", "configured"})
        top_metrics = [
            {"id": "portfolio", "label": "Portfolio", "value": f"Rs.{int(overview['portfolio']['portfolio_value']):,}", "tone": "neutral"},
            {
                "id": "regime",
                "label": "Regime",
                "value": str((overview["latest_mark"] or {}).get("details", {}).get("regime", "UNKNOWN")).replace("_", " "),
                "tone": "neutral",
            },
            {"id": "vix", "label": "VIX", "value": f"{float((overview['latest_mark'] or {}).get('details', {}).get('india_vix', 0.0)):.1f}", "tone": "cool"},
            {
                "id": "alpha",
                "label": "Alpha",
                "value": f"{float((overview['latest_mark'] or {}).get('alpha_pct') or 0.0):+.2f}%",
                "tone": "positive" if float((overview["latest_mark"] or {}).get("alpha_pct") or 0.0) >= 0 else "negative",
            },
            {"id": "win-rate", "label": "Win Rate", "value": f"{((sum(win_rates) / len(win_rates)) * 100):.0f}%" if win_rates else "--", "tone": "neutral"},
            {"id": "sharpe", "label": "Sharpe", "value": f"{float((latest_mark.details or {}).get('sharpe_63d', 0.0)):.2f}" if latest_mark else "--", "tone": "neutral"},
            {
                "id": "health",
                "label": "System",
                "value": f"{provider_ready}/{len(provider_health)} ready",
                "tone": "positive" if provider_ready == len(provider_health) else "warning",
            },
            {
                "id": "runtime",
                "label": "Runtime",
                "value": "Paused" if overview["runtime_state"]["autonomy_paused"] else "Active",
                "tone": "warning" if overview["runtime_state"]["autonomy_paused"] else "positive",
            },
        ]
        alerts = self._build_alerts(overview=overview, nodes=nodes)
        memory = self.memory_index()

        return {
            "updated_at": overview["market"]["timestamp_utc"],
            "top_metrics": top_metrics,
            "alerts": alerts,
            "stages": [{"id": stage_id, "label": label, "caption": caption} for stage_id, label, caption in STAGE_ORDER],
            "nodes": nodes,
            "boss": {
                "label": "BOSS",
                "status": "warning" if overview["runtime_state"]["autonomy_paused"] else "healthy",
                "value": f"{len(overview['latest_decisions'])} decisions",
                "caption": f"Threshold {self.settings.market.conviction_threshold:.2f}",
                "route": "/command",
            },
            "artifacts": [
                {"id": "trades", "label": "Trades", "caption": "Buy and sell log", "route": "/blotter", "value": str(len(self.repository.list_fills(limit=200)))},
                {"id": "positions", "label": "Positions", "caption": "Open positions", "route": "/portfolio", "value": str(len(self.repository.list_positions()))},
                {"id": "portfolio_state", "label": "Portfolio State", "caption": "Single-row snapshot", "route": "/portfolio", "value": "Live"},
                {"id": "signal_history", "label": "Signal History", "caption": "IC validation data", "route": "/blotter", "value": str(len(self.repository.list_signal_history(limit=200)))},
                {"id": "daily_pnl", "label": "Daily PnL", "caption": "EOD metrics and Sharpe", "route": "/portfolio", "value": str(len(marks))},
                {"id": "logs", "label": "Logs", "caption": "Pipeline, errors, agent outputs", "route": "/logs", "value": str(len(self.list_log_files()))},
                {"id": "reports", "label": "Reports", "caption": "Weekly reports", "route": "/reports", "value": str(len(self.list_report_files()))},
                {"id": "config", "label": "Config", "caption": "Pairs, holidays, thresholds", "route": "/config", "value": "Desk"},
            ],
            "memory_signal": {"nodes": len(memory["nodes"]), "edges": len(memory["edges"]), "route": "/memory"},
            "schedule": [
                {"id": job["id"], "label": job["name"], "value": _iso(job["next_run_time"]), "pending": job["pending"]}
                for job in overview["scheduler"]["jobs"][:8]
            ],
        }

    def system_map(self, *, overview: dict[str, Any] | None = None, force_refresh: bool = False) -> dict[str, Any]:
        if overview is not None:
            return self._build_system_map(overview=overview)
        return self._cached("system_map", 15.0, lambda: self._build_system_map(overview=self.overview()), force_refresh=force_refresh)

    def provider_health(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        if self._provider_health_cache is not None and self._provider_health_cached_at is not None:
            if now - self._provider_health_cached_at <= timedelta(seconds=60):
                return self._provider_health_cache
        screener_binary = Path(self.settings.screener.binary_path)
        yfinance = self.orchestrator.market_data.provider_health()
        nse = NSEClient().provider_health()
        cliproxy = self.gemini_oauth.runtime_status(start_service=True)
        holiday_calendar = holiday_calendar_status(self.settings, now_utc=now)
        payload = {
            "screener": {"status": "ready" if screener_binary.exists() else "missing", "binary": str(screener_binary)},
            "cliproxy": cliproxy,
            "exa": {"status": "configured" if self.settings.exa.api_keys else "disabled", "keys": len(self.settings.exa.api_keys)},
            "yfinance": yfinance,
            "nse": nse,
            "holiday_calendar": {
                "status": holiday_calendar.status,
                "ready": holiday_calendar.ready,
                "path": str(holiday_calendar.path),
                "fetched_at": _iso(holiday_calendar.fetched_at),
                "error": holiday_calendar.error,
            },
            "autonomous_universe": self._autonomous_universe_health(),
        }
        self._provider_health_cache = payload
        self._provider_health_cached_at = now
        return payload

    def _autonomous_universe_health(self) -> dict[str, Any]:
        runs = self.repository.list_agent_runs(limit=1, agent_id="agent_01_universe")
        if not runs:
            return {"status": "warming", "profile": None, "fallback_level": 0, "candidate_count": 0}
        artifacts = dict(runs[0].artifacts or {})
        discovery = dict(artifacts.get("universe_discovery") or {})
        return {
            "status": discovery.get("status") or "ready",
            "profile": discovery.get("final_profile") or discovery.get("selected_profile"),
            "fallback_level": int(discovery.get("fallback_level") or 0),
            "candidate_count": int(discovery.get("candidate_count") or artifacts.get("universe_size") or 0),
        }

    def scheduler_snapshot(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        heartbeat = self.repository.get_service_heartbeat("runner")
        running = False
        heartbeat_payload = None
        if heartbeat is not None:
            last_seen = heartbeat.last_seen
            if isinstance(last_seen, datetime) and last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=UTC)
            running = (now - last_seen) <= timedelta(seconds=30) and bool((heartbeat.details or {}).get("running", False))
            heartbeat_payload = {
                "service_name": heartbeat.service_name,
                "instance_id": heartbeat.instance_id,
                "last_seen": _iso(last_seen),
                "details": dict(heartbeat.details or {}),
            }
        jobs = []
        for spec in scheduled_job_specs():
            trigger = CronTrigger(timezone="Asia/Kolkata", **(spec.cron or {}))
            jobs.append(
                {
                    "id": spec.job_name,
                    "name": spec.job_name,
                    "next_run_time": _iso(trigger.get_next_fire_time(None, now)),
                    "pending": False,
                }
            )
        return {"running": running, "jobs": jobs, "runner": heartbeat_payload}

    def list_log_files(self) -> list[dict[str, Any]]:
        return self._list_files(self.settings.logs_dir)

    def read_log_file(self, relative_path: str) -> dict[str, Any]:
        return self._read_file(self.settings.logs_dir, relative_path)

    def list_report_files(self) -> list[dict[str, Any]]:
        return self._list_files(self.settings.reports_dir)

    def read_report_file(self, relative_path: str) -> dict[str, Any]:
        return self._read_file(self.settings.reports_dir, relative_path)

    def list_config_files(self) -> list[dict[str, Any]]:
        current_holidays = holiday_cache_path(self.settings)
        items: list[dict[str, Any]] = []
        for path in [self.settings.data_dir / "validated_pairs.json", current_holidays]:
            items.append(
                {
                    "relative_path": path.name,
                    "size_bytes": path.stat().st_size if path.exists() else 0,
                    "modified_at": _iso(datetime.fromtimestamp(path.stat().st_mtime, UTC)) if path.exists() else None,
                    "exists": path.exists(),
                }
            )
        return items

    def read_config_file(self, relative_path: str) -> dict[str, Any]:
        return self._read_file(self.settings.data_dir, relative_path)

    def runs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [_serialize_job(job) for job in self.repository.list_job_runs(limit=limit)]

    def job_requests(self, limit: int = 50) -> list[dict[str, Any]]:
        return [_serialize_job_request(row) for row in self.repository.list_job_requests(limit=limit)]

    def job_request_detail(self, request_id: str) -> dict[str, Any] | None:
        row = self.repository.get_job_request(request_id)
        return None if row is None else _serialize_job_request(row)

    def run_detail(self, run_id: str) -> dict[str, Any]:
        jobs = [job for job in self.repository.list_job_runs(limit=200) if job.id == run_id or (job.payload or {}).get("run_id") == run_id]
        agent_runs = self.repository.list_agent_runs(limit=200, run_id=run_id)
        decisions = self.repository.list_trade_decisions(run_id=run_id, limit=200)
        orders = [row for row in self.repository.list_orders(limit=200) if row.run_id == run_id]
        fills = [row for row in self.repository.list_fills(limit=200) if row.run_id == run_id]
        return {
            "run_id": run_id,
            "jobs": [_serialize_job(job) for job in jobs],
            "agent_runs": [_serialize_agent_run(row) for row in agent_runs],
            "decisions": [_serialize_decision(row) for row in decisions],
            "orders": [_serialize_order(row) for row in orders],
            "fills": [_serialize_fill(row) for row in fills],
        }

    def agents(self) -> list[dict[str, Any]]:
        latest_by_agent: dict[str, Any] = {}
        for row in self.repository.list_agent_runs(limit=200):
            latest_by_agent.setdefault(row.agent_id, row)
        ic_snapshot = self.repository.latest_ic_snapshot()
        reflections = {row.agent_id: row for row in self.repository.list_reflections(limit=100)}
        response: list[dict[str, Any]] = []
        for agent_id in sorted(set(latest_by_agent) | set(ic_snapshot) | set(reflections)):
            response.append(
                {
                    "agent_id": agent_id,
                    "latest_run": _serialize_agent_run(latest_by_agent[agent_id]) if agent_id in latest_by_agent else None,
                    "ic_snapshot": ic_snapshot.get(agent_id, {}),
                    "latest_reflection": _serialize_reflection(reflections[agent_id]) if agent_id in reflections else None,
                }
            )
        return response

    def agent_detail(self, agent_id: str) -> dict[str, Any]:
        rows = self.repository.list_agent_runs(limit=25, agent_id=agent_id)
        signals = self.repository.list_signal_history(agent_id=agent_id, limit=50)
        reflections = self.repository.list_reflections(agent_id=agent_id, limit=12)
        return {
            "agent_id": agent_id,
            "runs": [_serialize_agent_run(row) for row in rows],
            "signals": [
                {
                    "signal_date": row.signal_date.isoformat(),
                    "run_id": row.run_id,
                    "ticker": row.ticker,
                    "score": row.score,
                    "details": dict(row.details or {}),
                }
                for row in signals
            ],
            "reflections": [_serialize_reflection(row) for row in reflections],
            "ic_snapshot": self.repository.latest_ic_snapshot().get(agent_id, {}),
        }

    def _build_portfolio(self, *, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "snapshot": snapshot or self.orchestrator.live_portfolio_snapshot().model_dump(mode="json"),
            "positions": [_serialize_position(row) for row in self.repository.list_positions()],
            "orders": [_serialize_order(row) for row in self.repository.list_orders(limit=50)],
            "fills": [_serialize_fill(row) for row in self.repository.list_fills(limit=50)],
            "marks": [_serialize_mark(row) for row in self.repository.list_daily_marks(limit=30)],
            "decisions": [_serialize_decision(row) for row in self.repository.list_trade_decisions(limit=50)],
        }

    def portfolio(self, *, snapshot: dict[str, Any] | None = None, force_refresh: bool = False) -> dict[str, Any]:
        if snapshot is not None:
            return self._build_portfolio(snapshot=snapshot)
        return self._cached("portfolio", 15.0, lambda: self._build_portfolio(), force_refresh=force_refresh)

    def positions(self) -> list[dict[str, Any]]:
        return [_serialize_position(row) for row in self.repository.list_positions()]

    def orders(self, limit: int = 100) -> list[dict[str, Any]]:
        return [_serialize_order(row) for row in self.repository.list_orders(limit=limit)]

    def fills(self, limit: int = 100) -> list[dict[str, Any]]:
        return [_serialize_fill(row) for row in self.repository.list_fills(limit=limit)]

    def decisions(self, limit: int = 100) -> list[dict[str, Any]]:
        return [_serialize_decision(row) for row in self.repository.list_trade_decisions(limit=limit)]

    def marks(self, limit: int = 100) -> list[dict[str, Any]]:
        return [_serialize_mark(row) for row in self.repository.list_daily_marks(limit=limit)]

    def memory_index(self) -> dict[str, Any]:
        with self.repository.session_factory() as session:
            nodes = session.scalars(select(MemoryNode).order_by(MemoryNode.id.desc()).limit(30)).all()
            edges = session.scalars(select(MemoryEdge).order_by(MemoryEdge.id.desc()).limit(30)).all()
            return {
                "nodes": [
                    {
                        "id": row.id,
                        "node_type": row.node_type,
                        "ref_id": row.ref_id,
                        "content": row.content,
                        "details": dict(row.details or {}),
                    }
                    for row in nodes
                ],
                "edges": [
                    {
                        "id": row.id,
                        "source_ref": row.source_ref,
                        "target_ref": row.target_ref,
                        "relation": row.relation,
                        "details": dict(row.details or {}),
                    }
                    for row in edges
                ],
            }

    def memory_search(self, query: str) -> dict[str, Any]:
        return {"query": query, "results": self.repository.search_memory(query=query, limit=10)}

    def memory_detail(self, ref_id: str) -> dict[str, Any] | None:
        return self.repository.get_memory_node(ref_id)

    def config_snapshot(self) -> dict[str, Any]:
        runtime_state = self.repository.sync_entries_blocked_from_desk_messages()
        return {
            "settings": _sanitize_settings(settings_dict(self.settings)),
            "runtime_state": {**runtime_state, "updated_at": _iso(runtime_state.get("updated_at"))},
            "active_messages": [_serialize_message(row) for row in self.repository.list_desk_messages(active_only=True, limit=20)],
            "operator_actions": [_serialize_action(row) for row in self.repository.list_operator_actions(limit=20)],
            "overrides": self.repository.active_runtime_overrides(),
        }

    def gemini_oauth_settings(self) -> dict[str, Any]:
        return self.gemini_oauth.settings_snapshot()

    def update_gemini_oauth_settings(
        self,
        binary_path: str | None,
        *,
        login_mode: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        return self.gemini_oauth.update_settings(binary_path=binary_path, login_mode=login_mode, project_id=project_id)

    def install_gemini_oauth_cli_proxy(self) -> dict[str, Any]:
        return self.gemini_oauth.install_cli_proxy()

    def gemini_oauth_accounts(self) -> list[dict[str, Any]]:
        return self.gemini_oauth.list_accounts()

    def refresh_gemini_oauth_usage(self, account_id: str) -> dict[str, Any]:
        return self.gemini_oauth.refresh_usage(account_id=account_id)

    def delete_gemini_oauth_account(self, account_id: str) -> dict[str, Any]:
        return self.gemini_oauth.delete_account(account_id=account_id)

    def start_gemini_oauth_login(self, *, login_mode: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        return self.gemini_oauth.start_login(login_mode=login_mode, project_id=project_id)

    def gemini_oauth_login_session(self) -> dict[str, Any]:
        return self.gemini_oauth.login_session()

    def _list_files(self, root: Path) -> list[dict[str, Any]]:
        if not root.exists():
            return []
        files = [path for path in root.rglob("*") if path.is_file()]
        items = [
            {
                "relative_path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
                "modified_at": _iso(datetime.fromtimestamp(path.stat().st_mtime, UTC)),
            }
            for path in files
        ]
        return sorted(items, key=lambda item: (item["modified_at"] or "", item["relative_path"]), reverse=True)

    def _read_file(self, root: Path, relative_path: str) -> dict[str, Any]:
        candidate = (root / relative_path).resolve()
        base = root.resolve()
        if candidate != base and base not in candidate.parents:
            raise FileNotFoundError(relative_path)
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError(relative_path)
        text = candidate.read_text(encoding="utf-8", errors="replace")
        preview = text[:20_000]
        payload: dict[str, Any] = {
            "relative_path": str(candidate.relative_to(base)),
            "size_bytes": candidate.stat().st_size,
            "modified_at": _iso(datetime.fromtimestamp(candidate.stat().st_mtime, UTC)),
            "preview": preview,
            "truncated": len(text) > len(preview),
        }
        if candidate.suffix.lower() == ".json":
            try:
                payload["parsed"] = json.loads(text)
            except json.JSONDecodeError:
                payload["parsed"] = None
        return payload

    def _node_metric(
        self,
        *,
        agent_id: str,
        overview: dict[str, Any],
        ic_snapshot: dict[str, Any],
        signal_count: int,
        fill_count: int,
    ) -> dict[str, Any] | None:
        if agent_id == "agent_06_macro":
            value = float((overview["latest_mark"] or {}).get("details", {}).get("india_vix", 0.0))
            return {"label": "VIX", "value": f"{value:.1f}"}
        if agent_id == "agent_13_risk":
            return {"label": "Alerts", "value": str(len(overview["alerts"]))}
        if agent_id == "agent_14_execution":
            return {"label": "Fills", "value": str(fill_count)}
        if ic_snapshot.get("ic_value") is not None:
            return {"label": "IC", "value": f"{float(ic_snapshot['ic_value']):.3f}"}
        if ic_snapshot.get("win_rate") is not None:
            return {"label": "Win", "value": f"{float(ic_snapshot['win_rate']) * 100:.0f}%"}
        if signal_count:
            return {"label": "Rows", "value": str(signal_count)}
        return None

    def _node_summary(
        self,
        *,
        agent_id: str,
        overview: dict[str, Any],
        ic_snapshot: dict[str, Any],
        signal_count: int,
    ) -> str:
        if agent_id == "agent_06_macro":
            return str((overview["latest_mark"] or {}).get("details", {}).get("regime", "Regime pending")).replace("_", " ")
        if agent_id == "agent_13_risk":
            return overview["alerts"][0] if overview["alerts"] else "No active risk warnings."
        if agent_id == "agent_14_execution":
            return "Recent fills, charges, and execution types."
        if ic_snapshot.get("sample_size"):
            return f"{int(ic_snapshot['sample_size'])} samples in IC history."
        if signal_count:
            return f"{signal_count} recent signal rows."
        return "Awaiting fresh telemetry."

    def _build_alerts(self, *, overview: dict[str, Any], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        if overview["runtime_state"]["autonomy_paused"]:
            alerts.append(
                {
                    "id": "runtime-paused",
                    "severity": "critical",
                    "title": "Autonomy paused",
                    "detail": overview["runtime_state"].get("updated_reason") or "Operator pause active.",
                    "route": "/command",
                }
            )
        if not overview["scheduler"]["running"]:
            alerts.append(
                {
                    "id": "scheduler-stopped",
                    "severity": "critical",
                    "title": "Scheduler stopped",
                    "detail": "Scheduled jobs are not running.",
                    "route": "/command",
                }
            )
        for message in overview["alerts"]:
            alerts.append(
                {
                    "id": f"risk-{len(alerts)}",
                    "severity": "warning",
                    "title": "Risk warning",
                    "detail": message,
                    "route": "/config",
                }
            )
        for name, payload in overview["provider_health"].items():
            status = str(payload.get("status", "unknown"))
            if status not in {"ready", "configured"}:
                alerts.append(
                    {
                        "id": f"provider-{name}",
                        "severity": "warning",
                        "title": f"{name} attention",
                        "detail": status,
                        "route": "/config",
                    }
                )
        for action in overview["latest_actions"]:
            action_name = str(action.get("action") or "")
            payload = dict(action.get("payload") or {})
            if action_name == "startup.catchup_blocked":
                alerts.append(
                    {
                        "id": f"action-{action_name}",
                        "severity": "critical",
                        "title": "Startup catch-up blocked",
                        "detail": str(payload.get("reason") or "Missed trading slots could not be recovered."),
                        "route": "/command",
                    }
                )
            elif action_name == "startup.catchup_failed":
                alerts.append(
                    {
                        "id": f"action-{action_name}",
                        "severity": "critical",
                        "title": "Startup catch-up failed",
                        "detail": str(payload.get("slot") or "unknown slot"),
                        "route": "/command",
                    }
                )
        for node in nodes:
            if node["status"] == "critical":
                alerts.append(
                    {
                        "id": f"node-{node['id']}",
                        "severity": "critical",
                        "title": f"{node['label']} failed",
                        "detail": node["warnings"][0] if node["warnings"] else "Latest run failed.",
                        "route": node["route"],
                    }
                )
            elif node["status"] == "warning":
                alerts.append(
                    {
                        "id": f"node-warning-{node['id']}",
                        "severity": "warning",
                        "title": f"{node['label']} warning",
                        "detail": node["warnings"][0] if node["warnings"] else "Latest run emitted warnings.",
                        "route": node["route"],
                    }
                )
        alerts.sort(key=lambda item: (_severity_rank(item["severity"]), item["title"]))
        return alerts[:10]

    def desk_messages(self, active_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
        return [_serialize_message(row) for row in self.repository.list_desk_messages(active_only=active_only, limit=limit)]

    def operator_actions(self, limit: int = 50) -> list[dict[str, Any]]:
        return [_serialize_action(row) for row in self.repository.list_operator_actions(limit=limit)]

    def create_desk_message(self, raw_text: str, scope: str = "global", expires_in_hours: int | None = None) -> dict[str, Any]:
        expires_at = None if expires_in_hours is None else datetime.now(UTC) + timedelta(hours=expires_in_hours)
        row = self.repository.create_desk_message(raw_text=raw_text, scope=scope, expires_at=expires_at)
        parsed = dict(row.parsed_intent or {})
        if parsed.get("kind") == "pause_entries":
            self.repository.sync_entries_blocked_from_desk_messages()
        self.repository.log_operator_action("desk_message.create", {"message_id": row.id, "scope": scope, "parsed_intent": parsed})
        self._invalidate_snapshot_cache()
        return _serialize_message(row)

    def revoke_desk_message(self, message_id: str) -> dict[str, Any] | None:
        row = self.repository.revoke_desk_message(message_id)
        if row is None:
            return None
        self.repository.sync_entries_blocked_from_desk_messages()
        self.repository.log_operator_action("desk_message.revoke", {"message_id": message_id})
        self._invalidate_snapshot_cache()
        return _serialize_message(row)

    def pause_autonomy(self, reason: str) -> dict[str, Any]:
        state = self.repository.update_runtime_state(autonomy_paused=True, reason=reason)
        self.repository.log_operator_action("runtime.pause", {"reason": reason})
        self._invalidate_snapshot_cache()
        return {**state, "updated_at": _iso(state.get("updated_at"))}

    def resume_autonomy(self, reason: str) -> dict[str, Any]:
        state = self.repository.update_runtime_state(autonomy_paused=False, reason=reason)
        state = self.repository.sync_entries_blocked_from_desk_messages()
        self.repository.log_operator_action("runtime.resume", {"reason": reason})
        self._invalidate_snapshot_cache()
        return {**state, "updated_at": _iso(state.get("updated_at"))}

    def run_job_now(self, job_name: str) -> dict[str, Any]:
        if job_name not in manual_job_specs():
            raise KeyError(job_name)
        spec = get_job_spec(job_name)
        row = self.repository.enqueue_job_request(
            job_name=job_name,
            requested_by="web",
            payload=dict(spec.payload),
            dedupe_key=spec.dedupe_key or job_name,
        )
        payload = {
            "request_id": row.id,
            "job_name": row.job_name,
            "status": row.status,
        }
        self.repository.log_operator_action("job.run_now", payload)
        self._invalidate_snapshot_cache()
        return payload

    def force_exit(self, ticker: str, fraction: float = 1.0) -> dict[str, Any]:
        positions = {row.ticker: row for row in self.repository.list_positions()}
        if ticker not in positions:
            raise KeyError(ticker)
        job_name = "position-exit" if fraction >= 1.0 else "position-reduce"
        row = self.repository.enqueue_job_request(
            job_name=job_name,
            requested_by="web",
            payload={"ticker": ticker, "fraction": fraction},
            dedupe_key=f"{job_name}:{ticker}",
        )
        self.repository.log_operator_action("position.force_exit", {"ticker": ticker, "fraction": fraction, "request_id": row.id})
        self._invalidate_snapshot_cache()
        return {
            "request_id": row.id,
            "ticker": ticker,
            "fraction": fraction,
            "status": row.status,
        }

    def live_snapshot(self) -> dict[str, Any]:
        def _build() -> dict[str, Any]:
            overview = self.overview(force_refresh=True)
            return {
                "overview": overview,
                "system_map": self.system_map(overview=overview),
                "runs": self.runs(limit=50),
                "job_requests": self.job_requests(limit=50),
                "agents": self.agents(),
                "portfolio": self.portfolio(snapshot=overview["portfolio"]),
                "memory": self.memory_index(),
                "config": self.config_snapshot(),
            }

        return self._cached("live_snapshot", 15.0, _build)

    def websocket_snapshot(self) -> dict[str, Any]:
        return {"type": "snapshot.init", "payload": self.live_snapshot()}
