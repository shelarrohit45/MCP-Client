"""Detect failed CI runs and send alert emails."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from config import Settings
from email_client import send_email
from github_fetch import FailedRunSummary, GitHubFetchError, fetch_failed_ci_runs
from mcp_manager import MCPConnectionError


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


def build_ci_alert_body(settings: Settings, failures: list[FailedRunSummary]) -> str:
    lines = [
        f"CI failure alert for {settings.github_repo_full}",
        f"Failed runs in the last 24 hours: {len(failures)}",
        "",
    ]
    for index, failure in enumerate(failures, start=1):
        lines.extend(
            [
                f"Failure {index}:",
                f"  Workflow: {failure.workflow_name}",
                f"  Branch: {failure.branch}",
                f"  Author: {failure.author}",
                f"  Updated: {failure.updated_at}",
                f"  Link: {failure.url}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def run_ci_alert(settings: Settings, *, dry_run: bool = False, hours: int = 24) -> CiAlertResult:
    """Fetch failed CI runs and send a plain-text alert email."""
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

    body = build_ci_alert_body(settings, failures)
    subject = build_ci_alert_subject(settings, failures[0])

    if dry_run:
        print(textwrap.dedent(
            f"""
            --- Dry run: would send CI alert ---
            Subject: {subject}
            To: {', '.join(settings.email_recipients)}

            {body}
            """
        ).strip())
        return CiAlertResult(
            repo=settings.github_repo_full,
            failures=failures,
            sent=False,
            dry_run=True,
        )

    send_email(settings, subject=subject, body=body, html=False)
    print(f"CI alert sent for {len(failures)} failure(s).")
    return CiAlertResult(
        repo=settings.github_repo_full,
        failures=failures,
        sent=True,
        dry_run=False,
    )
