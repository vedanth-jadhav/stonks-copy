from __future__ import annotations

from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from quant_trading.jobs import scheduled_job_specs


def build_scheduler(enqueue_job: Callable[[str, dict | None, str], object]) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(
        timezone="Asia/Kolkata",
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 900},
    )
    for spec in scheduled_job_specs():
        scheduler.add_job(
            enqueue_job,
            CronTrigger(**(spec.cron or {})),
            args=[spec.job_name, dict(spec.payload), "scheduler"],
            id=spec.job_name,
            replace_existing=True,
        )
    return scheduler
