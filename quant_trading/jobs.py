from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class JobSpec:
    job_name: str
    handler_name: str
    cron: dict[str, Any] | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    manual_allowed: bool = True
    dedupe_key: str | None = None


JOB_SPECS: dict[str, JobSpec] = {
    "pipeline": JobSpec(job_name="pipeline", handler_name="run_pipeline", payload={"trigger": "manual:web"}),
    "startup-recovery": JobSpec(
        job_name="startup-recovery",
        handler_name="startup_recovery",
        cron={"hour": 8, "minute": 15, "day_of_week": "mon-fri"},
    ),
    "holiday-sync": JobSpec(
        job_name="holiday-sync",
        handler_name="sync_holidays",
        cron={"hour": 8, "minute": 16, "day_of_week": "mon-fri"},
    ),
    "morning-pipeline": JobSpec(
        job_name="morning-pipeline",
        handler_name="run_pipeline",
        cron={"hour": 9, "minute": 30, "day_of_week": "mon-fri"},
        payload={"trigger": "morning-pipeline"},
    ),
    "midday-pipeline": JobSpec(
        job_name="midday-pipeline",
        handler_name="run_pipeline",
        cron={"hour": 11, "minute": 30, "day_of_week": "mon-fri"},
        payload={"trigger": "midday-pipeline"},
    ),
    "afternoon-pipeline": JobSpec(
        job_name="afternoon-pipeline",
        handler_name="run_pipeline",
        cron={"hour": 13, "minute": 0, "day_of_week": "mon-fri"},
        payload={"trigger": "afternoon-pipeline"},
    ),
    "risk-final-pipeline": JobSpec(
        job_name="risk-final-pipeline",
        handler_name="run_pipeline",
        cron={"hour": 14, "minute": 30, "day_of_week": "mon-fri"},
        payload={"trigger": "risk-final-pipeline"},
    ),
    "eod-mark": JobSpec(
        job_name="eod-mark",
        handler_name="mark_end_of_day",
        cron={"hour": 15, "minute": 35, "day_of_week": "mon-fri"},
    ),
    "signal-backfill": JobSpec(
        job_name="signal-backfill",
        handler_name="run_backfill",
        cron={"hour": 16, "minute": 0, "day_of_week": "mon-fri"},
    ),
    "weekly-report": JobSpec(
        job_name="weekly-report",
        handler_name="write_weekly_report",
        cron={"hour": 16, "minute": 30, "day_of_week": "fri"},
    ),
    "portfolio-history-repair": JobSpec(
        job_name="portfolio-history-repair",
        handler_name="repair_portfolio_history",
    ),
    "nightly-reflection": JobSpec(
        job_name="nightly-reflection",
        handler_name="run_reflection",
        cron={"hour": 22, "minute": 0, "day_of_week": "mon-fri"},
    ),
    "pairs-revalidation": JobSpec(
        job_name="pairs-revalidation",
        handler_name="run_pairs_revalidation",
        cron={"hour": 9, "minute": 0, "day_of_week": "sun"},
    ),
    "position-exit": JobSpec(job_name="position-exit", handler_name="force_exit", payload={"fraction": 1.0}),
    "position-reduce": JobSpec(job_name="position-reduce", handler_name="force_exit", payload={"fraction": 0.5}),
}


def get_job_spec(job_name: str) -> JobSpec:
    return JOB_SPECS[job_name]


def scheduled_job_specs() -> list[JobSpec]:
    return [spec for spec in JOB_SPECS.values() if spec.cron is not None]


def manual_job_specs() -> dict[str, JobSpec]:
    return {name: spec for name, spec in JOB_SPECS.items() if spec.manual_allowed}
