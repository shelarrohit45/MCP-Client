"""Detect pull request lifecycle events and send email notifications."""

from __future__ import annotations

from dataclasses import dataclass, field

from config import Settings
from email_client import send_email
from github_pr import (
    PullRequestInfo,
    PullRequestReview,
    get_pull_request,
    get_pull_request_reviews,
    get_pull_request_status,
    list_recent_pull_requests,
)
from pr_event_emails import build_event_html, build_event_subject, build_event_text
from pr_event_state import PrEventState, PrSnapshot, load_pr_event_state, save_pr_event_state

SUPPORTED_EVENTS = {
    "created",
    "merged",
    "rejected",
    "reopened",
    "approved",
    "changes_requested",
    "ci_failed",
    "ci_passed",
}


@dataclass
class PrEvent:
    event_type: str
    pull_number: int
    reviewer: str = ""
    merged_by: str = ""
    review_id: int = 0
    ci_summary: str = ""


@dataclass
class PrEventsResult:
    checked: int
    sent: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    dry_run: bool = False


def _snapshot_from_pr(
    pr: PullRequestInfo,
    reviews: list[PullRequestReview],
    ci_state: str = "",
) -> PrSnapshot:
    return PrSnapshot(
        number=pr.number,
        state=pr.state,
        merged=pr.merged,
        title=pr.title,
        author=pr.author,
        url=pr.url,
        branch=pr.branch,
        review_ids={review.review_id for review in reviews if review.review_id},
        head_sha=pr.head_sha,
        ci_state=ci_state,
    )


def _detect_events(
    pr: PullRequestInfo,
    reviews: list[PullRequestReview],
    previous: PrSnapshot | None,
    ci_state: str,
) -> list[PrEvent]:
    events: list[PrEvent] = []

    if previous is None:
        if pr.state == "open":
            events.append(PrEvent(event_type="created", pull_number=pr.number))
        return events

    if previous.state == "open" and pr.state == "closed":
        if pr.merged:
            events.append(
                PrEvent(
                    event_type="merged",
                    pull_number=pr.number,
                    merged_by=pr.merged_by or "unknown",
                )
            )
        else:
            events.append(PrEvent(event_type="rejected", pull_number=pr.number))
    elif previous.state == "closed" and pr.state == "open":
        events.append(PrEvent(event_type="reopened", pull_number=pr.number))

    for review in reviews:
        if review.review_id in previous.review_ids:
            continue
        if review.state == "APPROVED":
            events.append(
                PrEvent(
                    event_type="approved",
                    pull_number=pr.number,
                    reviewer=review.reviewer,
                    review_id=review.review_id,
                )
            )
        elif review.state == "CHANGES_REQUESTED":
            events.append(
                PrEvent(
                    event_type="changes_requested",
                    pull_number=pr.number,
                    reviewer=review.reviewer,
                    review_id=review.review_id,
                )
            )

    if pr.state == "open" and previous and previous.ci_state and ci_state != previous.ci_state:
        if ci_state == "failure":
            events.append(
                PrEvent(
                    event_type="ci_failed",
                    pull_number=pr.number,
                    ci_summary=ci_state,
                )
            )
        elif ci_state == "success":
            events.append(
                PrEvent(
                    event_type="ci_passed",
                    pull_number=pr.number,
                    ci_summary=ci_state,
                )
            )

    return events


def _event_storage_key(event: PrEvent) -> str:
    if event.review_id:
        return f"{event.pull_number}:{event.event_type}:{event.review_id}"
    return f"{event.pull_number}:{event.event_type}"


def _send_event_email(
    settings: Settings,
    pr: PullRequestInfo,
    event: PrEvent,
    *,
    dry_run: bool,
) -> None:
    subject = build_event_subject(settings, event.event_type, pr)
    html_body = build_event_html(
        settings,
        event.event_type,
        pr,
        reviewer=event.reviewer,
        merged_by=event.merged_by,
        ci_summary=event.ci_summary,
    )
    text_body = build_event_text(
        settings,
        event.event_type,
        pr,
        reviewer=event.reviewer,
        merged_by=event.merged_by,
        ci_summary=event.ci_summary,
    )

    if dry_run:
        print(f"\n--- Dry run: would send {event.event_type} for PR #{pr.number} ---")
        print(f"Subject: {subject}")
        print(text_body)
        return

    send_email(settings, subject=subject, body=html_body, html=True)


def check_pr_events(
    settings: Settings,
    *,
    dry_run: bool = False,
    resend: bool = False,
    pr_number: int | None = None,
    event_types: set[str] | None = None,
) -> PrEventsResult:
    """Poll GitHub and email on PR lifecycle changes."""
    allowed = event_types or SUPPORTED_EVENTS
    state = load_pr_event_state()
    pull_requests = list_recent_pull_requests(settings)
    if pr_number is not None:
        pull_requests = [pr for pr in pull_requests if pr.number == pr_number]

    sent: list[str] = []
    skipped: list[str] = []

    for listed_pr in pull_requests:
        pr = get_pull_request(settings, listed_pr.number)
        reviews = get_pull_request_reviews(settings, pr.number) if pr.state == "open" else []
        ci_state = get_pull_request_status(settings, pr.number) if pr.state == "open" else ""
        previous = state.snapshots.get(pr.number)
        events = _detect_events(pr, reviews, previous, ci_state)

        for event in events:
            if event.event_type not in allowed:
                continue

            key = _event_storage_key(event)
            if state.was_sent(key) and not resend:
                skipped.append(key)
                continue

            _send_event_email(settings, pr, event, dry_run=dry_run)
            if not dry_run:
                state.mark_sent(key)
            sent.append(key)

        if not dry_run:
            state.snapshots[pr.number] = _snapshot_from_pr(pr, reviews, ci_state)

    if not dry_run:
        save_pr_event_state(state)

    return PrEventsResult(checked=len(pull_requests), sent=sent, skipped=skipped, dry_run=dry_run)


def print_pr_events_summary(result: PrEventsResult) -> None:
    mode = "Dry run" if result.dry_run else "Live"
    print(f"{mode}: checked {result.checked} pull request(s).")
    if result.sent:
        print("Sent: " + ", ".join(result.sent))
    else:
        print("No new PR event emails sent.")
    if result.skipped:
        print("Already sent: " + ", ".join(result.skipped[:10]) + ("..." if len(result.skipped) > 10 else ""))
