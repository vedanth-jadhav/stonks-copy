from quant_trading.scheduler import build_scheduler


def test_build_scheduler_registers_expected_jobs() -> None:
    scheduler = build_scheduler(lambda job_name, payload=None, requested_by="scheduler": None)
    job_ids = sorted(job.id for job in scheduler.get_jobs())
    assert job_ids == [
        "afternoon-pipeline",
        "eod-mark",
        "holiday-sync",
        "midday-pipeline",
        "morning-pipeline",
        "nightly-reflection",
        "pairs-revalidation",
        "risk-final-pipeline",
        "signal-backfill",
        "startup-recovery",
        "weekly-report",
    ]
