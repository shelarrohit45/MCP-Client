"""HTML email content for pull request lifecycle events."""

from __future__ import annotations

import html
import textwrap

from action_tokens import create_action_token
from config import Settings
from github_pr import CommitInfo, PullRequestInfo

EVENT_LABELS = {
    "created": "New Pull Request",
    "merged": "Pull Request Merged",
    "rejected": "Pull Request Rejected",
    "reopened": "Pull Request Reopened",
    "approved": "Pull Request Approved",
    "changes_requested": "Changes Requested",
    "ci_failed": "CI Failed",
    "ci_passed": "CI Passed",
    "pushed": "New Commits Pushed",
    "branch_push": "Code Pushed to Branch",
}

EVENT_SUBJECT_PREFIX = {
    "created": "[New PR]",
    "merged": "[PR Merged]",
    "rejected": "[PR Rejected]",
    "reopened": "[PR Reopened]",
    "approved": "[PR Approved]",
    "changes_requested": "[Changes Requested]",
    "ci_failed": "[CI Failed]",
    "ci_passed": "[CI Passed]",
    "pushed": "[Code Pushed]",
    "branch_push": "[Code Pushed]",
}


def _action_url(settings: Settings, pull_number: int, action: str) -> str:
    token = create_action_token(settings.action_secret, pull_number, action)
    return f"{settings.action_base_url}/pr/{pull_number}/{action}?token={token}"


def _action_buttons(settings: Settings, pr: PullRequestInfo) -> str:
    if pr.state != "open":
        return ""
    merge_url = _action_url(settings, pr.number, "merge")
    reject_url = _action_url(settings, pr.number, "reject")
    return f"""
    <p>
      <a href="{html.escape(merge_url)}"
         style="display:inline-block;padding:12px 18px;background:#1a7f37;color:#fff;
         text-decoration:none;border-radius:8px;font-weight:600;margin-right:12px;">
        Merge PR
      </a>
      <a href="{html.escape(reject_url)}"
         style="display:inline-block;padding:12px 18px;background:#cf222e;color:#fff;
         text-decoration:none;border-radius:8px;font-weight:600;">
        Reject PR
      </a>
    </p>
    """


def _pr_details(pr: PullRequestInfo, settings: Settings) -> str:
    description = html.escape(pr.body[:500] + ("..." if len(pr.body) > 500 else "")) or "No description."
    return f"""
    <p><strong>Repository:</strong> {html.escape(settings.github_repo_full)}</p>
    <p><strong>PR:</strong> <a href="{html.escape(pr.url)}">#{pr.number} {html.escape(pr.title)}</a></p>
    <p><strong>Author:</strong> {html.escape(pr.author)}<br>
    <strong>Branch:</strong> {html.escape(pr.branch)}</p>
    <p>{description}</p>
    """


def build_event_subject(settings: Settings, event_type: str, pr: PullRequestInfo) -> str:
    prefix = EVENT_SUBJECT_PREFIX.get(event_type, "[PR Update]")
    return f"{prefix} {settings.github_repo_full} — #{pr.number} {pr.title}"


def build_event_html(
    settings: Settings,
    event_type: str,
    pr: PullRequestInfo,
    *,
    reviewer: str = "",
    merged_by: str = "",
    ci_summary: str = "",
) -> str:
    heading = EVENT_LABELS.get(event_type, "Pull Request Update")
    extra = ""

    if event_type == "merged" and merged_by:
        extra = f"<p><strong>Merged by:</strong> {html.escape(merged_by)}</p>"
    elif event_type == "approved" and reviewer:
        extra = f"<p><strong>Approved by:</strong> {html.escape(reviewer)}</p>"
    elif event_type == "changes_requested" and reviewer:
        extra = f"<p><strong>Reviewed by:</strong> {html.escape(reviewer)}</p>"
    elif event_type in {"ci_failed", "ci_passed"} and ci_summary:
        extra = f"<p><strong>CI status:</strong> {html.escape(ci_summary)}</p>"
    elif event_type == "pushed" and ci_summary:
        extra = f"<p><strong>Latest commit:</strong> {html.escape(ci_summary)}</p>"

    buttons = _action_buttons(settings, pr) if event_type in {"created", "pushed"} else ""
    footer = """
    <p style="color:#555;font-size:14px;">
      Automated notification from MCP Client.
      For merge/reject actions, keep <code>python src/main.py action-server</code> running.
    </p>
  """

    return textwrap.dedent(
        f"""
        <h2>{html.escape(heading)}</h2>
        {_pr_details(pr, settings)}
        {extra}
        {buttons}
        {footer}
        """
    ).strip()


def build_event_text(
    settings: Settings,
    event_type: str,
    pr: PullRequestInfo,
    *,
    reviewer: str = "",
    merged_by: str = "",
    ci_summary: str = "",
) -> str:
    heading = EVENT_LABELS.get(event_type, "Pull Request Update")
    lines = [
        heading,
        f"Repository: {settings.github_repo_full}",
        f"PR #{pr.number}: {pr.title}",
        f"Author: {pr.author}",
        f"Branch: {pr.branch}",
        f"URL: {pr.url}",
    ]
    if merged_by:
        lines.append(f"Merged by: {merged_by}")
    if reviewer:
        lines.append(f"Reviewer: {reviewer}")
    if ci_summary:
        lines.append(f"Details: {ci_summary}")
    if event_type in {"created", "pushed"} and pr.state == "open":
        lines.extend(
            [
                f"Merge: {_action_url(settings, pr.number, 'merge')}",
                f"Reject: {_action_url(settings, pr.number, 'reject')}",
            ]
        )
    return "\n".join(lines)


def build_branch_push_subject(settings: Settings, branch: str, commit: CommitInfo) -> str:
    short_sha = commit.sha[:7] if commit.sha else "unknown"
    return f"[Code Pushed] {settings.github_repo_full} — {branch} ({short_sha})"


def build_branch_push_html(settings: Settings, branch: str, commit: CommitInfo) -> str:
    short_sha = html.escape(commit.sha[:7] if commit.sha else "unknown")
    return textwrap.dedent(
        f"""
        <h2>Code pushed to branch</h2>
        <p><strong>Repository:</strong> {html.escape(settings.github_repo_full)}</p>
        <p><strong>Branch:</strong> {html.escape(branch)}</p>
        <p><strong>Commit:</strong> <a href="{html.escape(commit.url)}">{short_sha}</a></p>
        <p><strong>Author:</strong> {html.escape(commit.author)}</p>
        <p><strong>Message:</strong> {html.escape(commit.message)}</p>
        <p style="color:#555;font-size:14px;">Automated notification from MCP Client.</p>
        """
    ).strip()


def build_branch_push_text(settings: Settings, branch: str, commit: CommitInfo) -> str:
    short_sha = commit.sha[:7] if commit.sha else "unknown"
    return "\n".join(
        [
            "Code pushed to branch",
            f"Repository: {settings.github_repo_full}",
            f"Branch: {branch}",
            f"Commit: {short_sha}",
            f"Author: {commit.author}",
            f"Message: {commit.message}",
            f"URL: {commit.url}",
        ]
    )
