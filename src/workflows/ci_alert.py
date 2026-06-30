"""Detect failed CI runs and send alert emails."""

from __future__ import annotations

import textwrap
from dataclasses import asdict, dataclass

from config import Settings
from email_client import send_email
from github_fetch import FailedRunSummary, GitHubFetchError, fetch_failed_ci_runs
from mcp_manager import MCPConnectionError
from template_renderer import TemplateRenderError, render_template


class CiAlertError(Exception):
    """Raised when CI alert workflow fails."""


@dataclass
class CiAlertResult:
    repo: str
    failures: list[FailedRunSummary]
    sent: bool
    dry_run: bool


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
    try:
        failures = fetch_failed_ci_runs(settings, hours=hours)
    except (GitHubFetchError, MCPConnectionError) as error:
        raise CiAlertError(f"Could not fetch failed CI runs: {error}") from error

    if not failures:
        print("No CI failures")
        return CiAlertResult(
            repo=settings.github_repo_full,
            failures=[],
            sent=False,
            dry_run=dry_run,
        )

    try:
        html_body = build_ci_alert_html(settings, failures, hours=hours)
    except TemplateRenderError as error:
        raise CiAlertError(str(error)) from error

    subject = build_ci_alert_subject(settings, failures[0])

    if dry_run:
        print(textwrap.dedent(
            f"""
            --- Dry run: would send CI alert ---
            Subject: {subject}
            To: {', '.join(settings.email_recipients)}

            {html_body}
            """
        ).strip())
        return CiAlertResult(
            repo=settings.github_repo_full,
            failures=failures,
            sent=False,
            dry_run=True,
        )

    send_email(settings, subject=subject, body=html_body, html=True)
    print(f"CI alert sent for {len(failures)} failure(s).")
    return CiAlertResult(
        repo=settings.github_repo_full,
        failures=failures,
        sent=True,
        dry_run=False,
    )
