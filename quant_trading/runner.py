from __future__ import annotations

import signal
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from quant_trading.jobs import get_job_spec
from quant_trading.main import build_runtime
from quant_trading.scheduler import build_scheduler


class Runner:
    def __init__(self, max_workers: int = 4) -> None:
        self.settings, self.repository, self.orchestrator, self.gemini_oauth = build_runtime()
        self.instance_id = f"{socket.gethostname()}:{threading.get_native_id()}"
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="runner-worker")
        self.active_requests: dict[str, str] = {}  # request_id -> job_name
        self.scheduler = build_scheduler(self.enqueue_job)
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, name="runner-heartbeat", daemon=True)

    def enqueue_job(self, job_name: str, payload: dict | None = None, requested_by: str = "runner") -> object:
        spec = get_job_spec(job_name)
        merged_payload = {**spec.payload, **(payload or {})}
        return self.repository.enqueue_job_request(
            job_name=job_name,
            requested_by=requested_by,
            payload=merged_payload,
            dedupe_key=spec.dedupe_key or job_name,
        )

    def _heartbeat_loop(self) -> None:
        while not self.stop_event.wait(5):
            for request_id in list(self.active_requests.keys()):
                self.repository.heartbeat_job_request(request_id=request_id, lease_owner=self.instance_id)
            self.repository.record_service_heartbeat(
                service_name="runner",
                instance_id=self.instance_id,
                details={
                    "running": True,
                    "active_jobs": list(self.active_requests.values()),
                    "queue_depth": self.repository.count_active_job_requests(),
                },
            )

    def _dispatch(self, job_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        spec = get_job_spec(job_name)
        handler_name = spec.handler_name
        if handler_name == "run_pipeline":
            result = self.orchestrator.run_pipeline(trigger=str(payload.get("trigger") or job_name))
            return {"run_id": result.run_id}
        if handler_name == "startup_recovery":
            self.orchestrator.startup_recovery()
            return {}
        if handler_name == "sync_holidays":
            path = self.orchestrator.sync_holidays()
            return {"path": str(path)}
        if handler_name == "mark_end_of_day":
            self.orchestrator.mark_end_of_day()
            return {}
        if handler_name == "run_backfill":
            summary = self.orchestrator.run_backfill()
            return summary.model_dump(mode="json") if hasattr(summary, "model_dump") else {"status": "ok"}
        if handler_name == "write_weekly_report":
            path = self.orchestrator.write_weekly_report()
            return {"path": str(path)}
        if handler_name == "repair_portfolio_history":
            return self.orchestrator.repair_portfolio_history()
        if handler_name == "run_reflection":
            self.orchestrator.run_reflection(self.orchestrator.agents.keys())
            return {}
        if handler_name == "run_pairs_revalidation":
            result = self.orchestrator.run_pairs_revalidation()
            return {"count": len(result)}
        if handler_name == "force_exit":
            return self.orchestrator.force_exit(
                ticker=str(payload["ticker"]),
                fraction=float(payload.get("fraction", 1.0)),
            )
        raise KeyError(f"Unsupported handler '{handler_name}' for job '{job_name}'.")

    def _execute_request(self, request: Any) -> None:
        self.active_requests[request.id] = request.job_name
        try:
            result = self._dispatch(request.job_name, dict(request.payload or {}))
            self.repository.complete_job_request(request.id, result=result, run_id=result.get("run_id"))
        except Exception as exc:
            self.repository.fail_job_request(
                request.id,
                error=str(exc),
                result={"job_name": request.job_name},
            )
        finally:
            self.active_requests.pop(request.id, None)

    def run_forever(self) -> None:
        self.orchestrator.startup_recovery()
        self.repository.recover_expired_job_requests(now=datetime.now(UTC))
        self.repository.record_service_heartbeat(
            service_name="runner",
            instance_id=self.instance_id,
            details={"running": True, "active_jobs": [], "queue_depth": 0},
        )
        self._heartbeat_thread.start()
        self.scheduler.start()
        self.enqueue_job("pipeline", {"trigger": "bootstrap"}, "runner")
        while not self.stop_event.is_set():
            if len(self.active_requests) >= self.executor._max_workers:
                time.sleep(0.5)
                continue
            request = self.repository.claim_next_job_request(lease_owner=self.instance_id)
            if request is None:
                time.sleep(1)
                continue
            self.executor.submit(self._execute_request, request)

        self.executor.shutdown(wait=True)
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.repository.record_service_heartbeat(
            service_name="runner",
            instance_id=self.instance_id,
            details={"running": False, "active_jobs": [], "queue_depth": 0},
        )


def main() -> None:
    runner = Runner()

    def _request_stop(signum, frame) -> None:  # pragma: no cover - signal integration
        _ = signum, frame
        runner.stop_event.set()

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
    runner.run_forever()
