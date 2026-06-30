"""Collect repository activity and send a daily digest email."""

from __future__ import annotations

import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from config import Settings
from email_client import send_email
from github_fetch import (
    FailedRunSummary,
    GitHubFetchError,
    PullRequestSummary,
    ReleaseSummary,
    fetch_failed_ci_runs,
    fetch_latest_release,
    fetch_open_issue_count,
    fetch_open_pull_requests,
    fetch_successful_ci_runs,
)
from mcp_manager import MCPConnectionError
from template_renderer import TemplateRenderError, render_template


class DailyDigestError(Exception):
    """Raised when the daily digest workflow fails."""


@dataclass
class DigestData:
    repo: str
    date: str
    open_prs: list[PullRequestSummary]
    open_issue_count: int
    failed_ci: list[FailedRunSummary]
    successful_ci: list[FailedRunSummary]
    latest_release: ReleaseSummary | None
    errors: list[str]


@dataclass
class DigestResult:
    data: DigestData
    sent: bool
    dry_run: bool


def digest_date_label(when: datetime | None = None) -> str:
    """Return the date string used in digest subject lines."""
    moment = when or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%d")


def build_digest_subject(settings: Settings, date: str) -> str:
    return f"[Daily Digest] {settings.github_repo_full} — {date}"


def fetch_digest_data(settings: Settings, *, hours: int = 24) -> DigestData:
    """Collect digest data from GitHub MCP, tolerating partial failures."""
    errors: list[str] = []
    date = digest_date_label()

    open_prs: list[PullRequestSummary] = []
    try:
        open_prs = fetch_open_pull_requests(settings)
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"open PRs: {error}")

    open_issue_count = 0
    try:
        open_issue_count = fetch_open_issue_count(settings)
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"open issues: {error}")

    failed_ci: list[FailedRunSummary] = []
    try:
        failed_ci = fetch_failed_ci_runs(settings, hours=hours)
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"failed CI: {error}")

    successful_ci: list[FailedRunSummary] = []
    try:
        successful_ci = fetch_successful_ci_runs(settings, hours=hours)
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"successful CI: {error}")

    latest_release: ReleaseSummary | None = None
    try:
        latest_release = fetch_latest_release(settings)
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"latest release: {error}")

    return DigestData(
        repo=settings.github_repo_full,
        date=date,
        open_prs=open_prs,
        open_issue_count=open_issue_count,
        failed_ci=failed_ci,
        successful_ci=successful_ci,
        latest_release=latest_release,
        errors=errors,
    )


def build_digest_html(settings: Settings, data: DigestData, *, hours: int = 24) -> str:
    return render_template(
        "digest.html",
        repo=data.repo,
        date=data.date,
        hours=hours,
        open_pr_count=len(data.open_prs),
        open_prs=[asdict(pr) for pr in data.open_prs],
        open_issue_count=data.open_issue_count,
        failed_ci_count=len(data.failed_ci),
        failed_ci=[asdict(run) for run in data.failed_ci],
        successful_ci_count=len(data.successful_ci),
        successful_ci=[asdict(run) for run in data.successful_ci],
        latest_release=asdict(data.latest_release) if data.latest_release else None,
        errors=data.errors,
    )


def print_digest_summary(data: DigestData) -> None:
    print(f"Repository: {data.repo}")
    print(f"Date: {data.date}")
    print(f"Open PRs: {len(data.open_prs)}")
    print(f"Open issues: {data.open_issue_count}")
    print(f"Failed CI (last 24h): {len(data.failed_ci)}")
    print(f"Successful CI (last 24h): {len(data.successful_ci)}")
    if data.latest_release:
        print(f"Latest release: {data.latest_release.tag_name} ({data.latest_release.published_at})")
    else:
        print("Latest release: none")
    if data.errors:
        print("\nWarnings:")
        for error in data.errors:
            print(f"- {error}")


def run_daily_digest(
    settings: Settings,
    *,
    dry_run: bool = False,
    send: bool = False,
    hours: int = 24,
) -> DigestResult:
    """Fetch digest data and optionally send the digest email."""
    data = fetch_digest_data(settings, hours=hours)

    if data.errors and not any(
        [
            data.open_prs,
            data.open_issue_count,
            data.failed_ci,
            data.successful_ci,
            data.latest_release,
        ]
    ):
        raise DailyDigestError(
            "Could not fetch any digest data:\n" + "\n".join(f"- {e}" for e in data.errors)
        )

    try:
        html_body = build_digest_html(settings, data, hours=hours)
    except TemplateRenderError as error:
        raise DailyDigestError(str(error)) from error

    subject = build_digest_subject(settings, data.date)
    print_digest_summary(data)

    if dry_run:
        print(
            textwrap.dedent(
                f"""
                --- Dry run: would send daily digest ---
                Subject: {subject}
                To: {', '.join(settings.email_recipients)}

                {html_body}
                """
            ).strip()
        )
        return DigestResult(data=data, sent=False, dry_run=True)

    if send:
        send_email(settings, subject=subject, body=html_body, html=True)
        print("Daily digest sent.")
        return DigestResult(data=data, sent=True, dry_run=False)

    raise DailyDigestError("Use --dry-run or --send")
