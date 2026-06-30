"""GitHub pull request operations via MCP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from config import Settings
from github_fetch import GitHubFetchError, _author_login, _parse_tool_json, _pr_branch
from mcp_manager import MCPConnectionError, call_github_tool_sync, extract_text_result
from mcp.types import CallToolResult


@dataclass
class PullRequestInfo:
    number: int
    title: str
    author: str
    url: str
    branch: str
    state: str
    created_at: str
    body: str
    merged: bool = False
    merged_by: str = ""
    draft: bool = False
    head_sha: str = ""


@dataclass
class PullRequestReview:
    review_id: int
    state: str
    reviewer: str
    body: str
    submitted_at: str


@dataclass
class CommitInfo:
    sha: str
    message: str
    author: str
    url: str


class PullRequestActionError(Exception):
    """Raised when merge or close actions fail."""


    """Raised when merge or close actions fail."""


def _summarize_pull_request(item: dict[str, Any]) -> PullRequestInfo:
    head = item.get("head") or {}
    merged_by = item.get("merged_by")
    merged_by_login = ""
    if isinstance(merged_by, dict):
        merged_by_login = str(merged_by.get("login", ""))
    elif isinstance(merged_by, str):
        merged_by_login = merged_by

    return PullRequestInfo(
        number=int(item.get("number", 0)),
        title=str(item.get("title", "Untitled")),
        author=_author_login(item),
        url=str(item.get("html_url", "")),
        branch=_pr_branch(item),
        state=str(item.get("state", "unknown")),
        created_at=str(item.get("created_at", "")),
        body=str(item.get("body") or "").strip(),
        merged=bool(item.get("merged", False)),
        merged_by=merged_by_login,
        draft=bool(item.get("draft", False)),
        head_sha=str(head.get("sha", "")),
    )


def _summarize_review(item: dict[str, Any]) -> PullRequestReview:
    user = item.get("user") or {}
    return PullRequestReview(
        review_id=int(item.get("id", 0)),
        state=str(item.get("state", "")),
        reviewer=str(user.get("login", "unknown")),
        body=str(item.get("body") or "").strip(),
        submitted_at=str(item.get("submitted_at", "")),
    )


def _list_pull_requests(settings: Settings, state: str) -> list[PullRequestInfo]:
    result = call_github_tool_sync(
        settings.github_token,
        "list_pull_requests",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "state": state,
            "perPage": 30,
            "sort": "updated",
            "direction": "desc",
        },
    )
    data = _parse_tool_json(result, "list_pull_requests")
    if not isinstance(data, list):
        return []
    return [_summarize_pull_request(item) for item in data if isinstance(item, dict)]


def list_open_pull_requests(settings: Settings) -> list[PullRequestInfo]:
    """Return open pull requests for the configured repository."""
    return _list_pull_requests(settings, "open")


def list_recent_pull_requests(settings: Settings) -> list[PullRequestInfo]:
    """Return open and recently updated closed pull requests."""
    by_number: dict[int, PullRequestInfo] = {}
    for state in ("open", "closed"):
        for pr in _list_pull_requests(settings, state):
            by_number[pr.number] = pr
    return sorted(by_number.values(), key=lambda pr: pr.number, reverse=True)


def get_pull_request_status(settings: Settings, pull_number: int) -> str:
    """Return combined CI status for a pull request head commit."""
    result = call_github_tool_sync(
        settings.github_token,
        "pull_request_read",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "pullNumber": pull_number,
            "method": "get_status",
        },
    )
    data = _parse_tool_json(result, "pull_request_read")
    if isinstance(data, dict):
        return str(data.get("state", "unknown"))
    return "unknown"


def get_pull_request_reviews(settings: Settings, pull_number: int) -> list[PullRequestReview]:
    """Return reviews submitted on a pull request."""
    result = call_github_tool_sync(
        settings.github_token,
        "pull_request_read",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "pullNumber": pull_number,
            "method": "get_reviews",
            "perPage": 100,
        },
    )
    data = _parse_tool_json(result, "pull_request_read")
    if not isinstance(data, list):
        return []
    return [_summarize_review(item) for item in data if isinstance(item, dict)]


def get_pull_request_commits(settings: Settings, pull_number: int, per_page: int = 1) -> list[CommitInfo]:
    """Return recent commits on a pull request branch."""
    result = call_github_tool_sync(
        settings.github_token,
        "pull_request_read",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "pullNumber": pull_number,
            "method": "get_commits",
            "perPage": per_page,
        },
    )
    return _summarize_commits(_parse_tool_json(result, "pull_request_read"))


def get_branch_commits(settings: Settings, branch: str = "main", per_page: int = 5) -> list[CommitInfo]:
    """Return recent commits on a repository branch."""
    result = call_github_tool_sync(
        settings.github_token,
        "list_commits",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "sha": branch,
            "perPage": per_page,
        },
    )
    return _summarize_commits(_parse_tool_json(result, "list_commits"))


def _summarize_commits(data: Any) -> list[CommitInfo]:
    if not isinstance(data, list):
        return []
    commits: list[CommitInfo] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        author_name = str(author.get("name") or author.get("login") or "unknown")
        user = item.get("author") or {}
        if user.get("login"):
            author_name = str(user.get("login"))
        commits.append(
            CommitInfo(
                sha=str(item.get("sha", "")),
                message=str(commit.get("message", "")).splitlines()[0] or "No message",
                author=author_name,
                url=str(item.get("html_url", "")),
            )
        )
    return commits


def get_pull_request(settings: Settings, pull_number: int) -> PullRequestInfo:
    """Fetch a single pull request."""
    result = call_github_tool_sync(
        settings.github_token,
        "pull_request_read",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "pullNumber": pull_number,
            "method": "get",
        },
    )
    data = _parse_tool_json(result, "pull_request_read")
    if not isinstance(data, dict):
        raise PullRequestActionError(f"Could not load PR #{pull_number}.")
    return _summarize_pull_request(data)


def merge_pull_request(settings: Settings, pull_number: int) -> str:
    """Merge an open pull request."""
    result = call_github_tool_sync(
        settings.github_token,
        "merge_pull_request",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "pullNumber": pull_number,
            "merge_method": "merge",
        },
    )
    return _action_result_message(result, f"PR #{pull_number} merged.")


def reject_pull_request(settings: Settings, pull_number: int) -> str:
    """Close (reject) an open pull request."""
    result = call_github_tool_sync(
        settings.github_token,
        "update_pull_request",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "pullNumber": pull_number,
            "state": "closed",
        },
    )
    return _action_result_message(result, f"PR #{pull_number} rejected (closed).")


def _action_result_message(result: CallToolResult, success_fallback: str) -> str:
    if result.isError:
        message = extract_text_result(result).strip() or "GitHub action failed."
        if "403" in message and "personal access token" in message.lower():
            raise PullRequestActionError(
                f"{message}\n\n"
                "Your GitHub token can read PRs but cannot merge/close them.\n"
                "Fix: GitHub → Settings → Developer settings → Fine-grained tokens\n"
                "Edit your token for repo MCP-Client and enable:\n"
                "  • Pull requests: Read and write\n"
                "  • Contents: Read and write\n"
                "Then update GITHUB_PERSONAL_ACCESS_TOKEN in .env if you create a new token."
            )
        raise PullRequestActionError(message)

    if result.structuredContent is not None:
        return json.dumps(result.structuredContent)

    text = extract_text_result(result).strip()
    return text or success_fallback
