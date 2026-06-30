"""APScheduler jobs for digest and CI alert automation."""

from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app_logging import get_logger, log_workflow_end, log_workflow_start
from config import Settings
from error_messages import format_error_for_user
from workflows.ci_alert import run_ci_alert
from workflows.daily_digest import run_daily_digest

logger = get_logger("scheduler")


class SchedulerError(Exception):
    """Raised when the scheduler cannot be started."""


def parse_digest_time(digest_time: str) -> tuple[int, int]:
    """Parse HH:MM from config into hour and minute."""
    parts = digest_time.strip().split(":")
    if len(parts) != 2:
        raise SchedulerError(
            f"Invalid digest_time '{digest_time}'. Expected 24-hour format like 09:00."
        )
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as error:
        raise SchedulerError(
            f"Invalid digest_time '{digest_time}'. Expected 24-hour format like 09:00."
        ) from error

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise SchedulerError(
            f"Invalid digest_time '{digest_time}'. Hour must be 0-23 and minute 0-59."
        )
    return hour, minute


def _run_ci_alert_job(settings: Settings) -> None:
    log_workflow_start(logger, "scheduled_ci_alert")
    try:
        run_ci_alert(settings, dry_run=False)
        log_workflow_end(logger, "scheduled_ci_alert", success=True)
    except Exception as error:  # noqa: BLE001 - keep scheduler running
        message = format_error_for_user(error)
        logger.exception("scheduled_ci_alert failed: %s", message)
        log_workflow_end(logger, "scheduled_ci_alert", success=False, detail=message)
        print(f"CI alert job failed: {message}")


def _run_digest_job(settings: Settings) -> None:
    log_workflow_start(logger, "scheduled_digest")
    try:
        run_daily_digest(settings, send=True)
        log_workflow_end(logger, "scheduled_digest", success=True)
    except Exception as error:  # noqa: BLE001 - keep scheduler running
        message = format_error_for_user(error)
        logger.exception("scheduled_digest failed: %s", message)
        log_workflow_end(logger, "scheduled_digest", success=False, detail=message)
        print(f"Digest job failed: {message}")


def build_scheduler(settings: Settings) -> BlockingScheduler:
    """Create a scheduler with digest and CI alert jobs (does not start it)."""
    hour, minute = parse_digest_time(settings.digest_time)
    scheduler = BlockingScheduler()

    scheduler.add_job(
        _run_ci_alert_job,
        IntervalTrigger(minutes=settings.ci_check_interval_minutes),
        args=[settings],
        id="ci_alert",
        name="CI failure alert check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_digest_job,
        CronTrigger(hour=hour, minute=minute),
        args=[settings],
        id="daily_digest",
        name="Daily digest email",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def run_scheduler(settings: Settings) -> None:
    """Start the blocking scheduler loop."""
    scheduler = build_scheduler(settings)
    print("Scheduler started. Press Ctrl+C to stop.")
    print(f"- Daily digest: every day at {settings.digest_time} (local time)")
    print(f"- CI alert check: every {settings.ci_check_interval_minutes} minute(s)")
    print(f"- Logs: logs/app.log")
    logger.info(
        "scheduler_started digest_time=%s ci_interval_minutes=%s",
        settings.digest_time,
        settings.ci_check_interval_minutes,
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
