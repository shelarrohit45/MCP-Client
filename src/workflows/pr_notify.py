"""Notify recipients when new pull requests are opened."""

from __future__ import annotations

from dataclasses import dataclass

from config import Settings
from workflows.pr_events import PrEventsResult, check_pr_events, print_pr_events_summary


@dataclass
class PrNotifyResult:
    checked: int
    notified: list[int]
    skipped_already_notified: list[int]
    dry_run: bool


def notify_new_pull_requests(
    settings: Settings,
    *,
    dry_run: bool = False,
    resend: bool = False,
    pr_number: int | None = None,
) -> PrNotifyResult:
    """Send notifications when new pull requests are opened."""
    result = check_pr_events(
        settings,
        dry_run=dry_run,
        resend=resend,
        pr_number=pr_number,
        event_types={"created"},
    )
    notified = [int(key.split(":")[0]) for key in result.sent]
    skipped = [int(key.split(":")[0]) for key in result.skipped]
    return PrNotifyResult(
        checked=result.checked,
        notified=notified,
        skipped_already_notified=skipped,
        dry_run=result.dry_run,
    )


def print_pr_notify_summary(result: PrNotifyResult, *, resend: bool = False) -> None:
    events_result = PrEventsResult(
        checked=result.checked,
        sent=[f"{number}:created" for number in result.notified],
        skipped=[f"{number}:created" for number in result.skipped_already_notified],
        dry_run=result.dry_run,
    )
    print_pr_events_summary(events_result)
