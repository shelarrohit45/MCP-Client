"""Detect failed CI runs and send alert emails."""

from __future__ import annotations

import textwrap
from dataclasses import asdict, dataclass

from app_logging import get_logger, log_workflow_end, log_workflow_start
from config import Settings
from email_client import EmailSendError, send_email
from github_fetch import FailedRunSummary, GitHubFetchError, fetch_failed_ci_runs
from mcp_manager import MCPConnectionError
from template_renderer import TemplateRenderError, render_template
from workflow_state import load_workflow_state, save_workflow_state

logger = get_logger("ci_alert")


class CiAlertError(Exception):
    """Raised when CI alert workflow fails."""


@dataclass
class CiAlertResult:
    repo: str
    failures: list[FailedRunSummary]
    sent: bool
    dry_run: bool
    skipped_duplicates: int = 0


def filter_new_failures(
    failures: list[FailedRunSummary],
    alerted_run_ids: set[str],
) -> tuple[list[FailedRunSummary], int]:
    """Return failures that have not already been alerted."""
    new_failures: list[FailedRunSummary] = []
    skipped = 0
    for failure in failures:
        if failure.run_id in alerted_run_ids:
            skipped += 1
            continue
        new_failures.append(failure)
    return new_failures, skipped


def build_ci_alert_subject(settings: Settings, failure: FailedRunSummary) -> str:
    return f"[CI FAILED] {settings.github_repo_full} — {failure.workflow_name}"


def build_ci_alert_html(
    settings: Settings,
    failures: list[FailedRunSummary],
    *,
    hours: int = 24,
) -> str:
    return render_template(
        "ci_alert.html",
        repo=settings.github_repo_full,
        failure_count=len(failures),
        hours=hours,
        failures=[asdict(failure) for failure in failures],
    )


def run_ci_alert(settings: Settings, *, dry_run: bool = False, hours: int = 24) -> CiAlertResult:
    """Fetch failed CI runs and send an HTML alert email."""
    log_workflow_start(logger, "ci_alert", dry_run=dry_run, hours=hours)

    try:
        failures = fetch_failed_ci_runs(settings, hours=hours)
    except (GitHubFetchError, MCPConnectionError) as error:
        log_workflow_end(logger, "ci_alert", success=False, detail=str(error))
        raise CiAlertError(f"Could not fetch failed CI runs: {error}") from error

    if not failures:
        print("No CI failures")
        log_workflow_end(logger, "ci_alert", success=True, detail="no_failures")
        return CiAlertResult(
            repo=settings.github_repo_full,
            failures=[],
            sent=False,
            dry_run=dry_run,
        )

    state = load_workflow_state()
    new_failures, skipped = filter_new_failures(failures, state.alerted_run_ids)

    if skipped:
        logger.info("skipped_duplicate_alerts count=%s", skipped)

    if not new_failures:
        print(f"No new CI failures to alert ({skipped} already notified).")
        log_workflow_end(
            logger,
            "ci_alert",
            success=True,
            detail=f"all_duplicates skipped={skipped}",
        )
        return CiAlertResult(
            repo=settings.github_repo_full,
            failures=failures,
            sent=False,
            dry_run=dry_run,
            skipped_duplicates=skipped,
        )

    try:
        html_body = build_ci_alert_html(settings, new_failures, hours=hours)
    except TemplateRenderError as error:
        log_workflow_end(logger, "ci_alert", success=False, detail=str(error))
        raise CiAlertError(str(error)) from error

    subject = build_ci_alert_subject(settings, new_failures[0])

    if dry_run:
        print(textwrap.dedent(
            f"""
            --- Dry run: would send CI alert ---
            Subject: {subject}
            To: {', '.join(settings.email_recipients)}
            New failures: {len(new_failures)} (skipped {skipped} duplicate(s))

            {html_body}
            """
        ).strip())
        log_workflow_end(
            logger,
            "ci_alert",
            success=True,
            detail=f"dry_run new={len(new_failures)} skipped={skipped}",
        )
        return CiAlertResult(
            repo=settings.github_repo_full,
            failures=new_failures,
            sent=False,
            dry_run=True,
            skipped_duplicates=skipped,
        )

    try:
        send_email(settings, subject=subject, body=html_body, html=True)
    except EmailSendError as error:
        log_workflow_end(logger, "ci_alert", success=False, detail=str(error))
        raise CiAlertError(str(error)) from error

    for failure in new_failures:
        state.mark_alerted(failure.run_id)
    save_workflow_state(state)

    print(f"CI alert sent for {len(new_failures)} new failure(s).")
    if skipped:
        print(f"Skipped {skipped} failure(s) already alerted.")
    log_workflow_end(
        logger,
        "ci_alert",
        success=True,
        detail=f"sent={len(new_failures)} skipped={skipped}",
    )
    return CiAlertResult(
        repo=settings.github_repo_full,
        failures=new_failures,
        sent=True,
        dry_run=False,
        skipped_duplicates=skipped,
    )
