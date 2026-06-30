"""Fetch GitHub repository data via MCP tools."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import Settings
from mcp_manager import MCPConnectionError, call_github_tool_sync, extract_text_result
from mcp.types import CallToolResult

try:
    from mcp.shared.exceptions import McpError
except ImportError:
    McpError = Exception  # type: ignore[misc, assignment]

ROOT = Path(__file__).resolve().parent.parent
GITHUB_SAMPLE_PATH = ROOT / "logs" / "github_sample.json"


class GitHubFetchError(Exception):
    """Raised when GitHub MCP tool calls fail."""


@dataclass
class PullRequestSummary:
    number: int
    title: str
    author: str
    url: str
    branch: str
    state: str


@dataclass
class FailedRunSummary:
    run_id: str
    title: str
    workflow_name: str
    branch: str
    author: str
    url: str
    updated_at: str


@dataclass
class ReleaseSummary:
    tag_name: str
    name: str
    author: str
    published_at: str
    url: str


@dataclass
class GitHubFetchResult:
    repo: str
    fetched_at: str
    open_pull_requests: list[PullRequestSummary]
    failed_runs: list[FailedRunSummary]
    raw: dict[str, Any]
    errors: list[str]


def _parse_tool_json(result: CallToolResult, tool_name: str) -> Any:
    if result.isError:
        message = extract_text_result(result).strip() or f"{tool_name} failed"
        raise GitHubFetchError(message)

    if result.structuredContent is not None:
        return result.structuredContent

    text = extract_text_result(result).strip()
    if not text:
        return []

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise GitHubFetchError(f"{tool_name} returned non-JSON data: {text[:200]}") from error


def _author_login(item: dict[str, Any]) -> str:
    user = item.get("user") or {}
    return str(user.get("login", "unknown"))


def _pr_branch(item: dict[str, Any]) -> str:
    head = item.get("head") or {}
    return str(head.get("ref", "unknown"))


def _ci_run_id(item: dict[str, Any]) -> str:
    updated_at = str(item.get("updated_at", ""))
    issue_id = item.get("id")
    if issue_id is not None:
        return f"{issue_id}:{updated_at}"
    number = item.get("number", 0)
    return f"pr-{number}:{updated_at}"


def _summarize_pull_requests(data: Any) -> list[PullRequestSummary]:
    if not isinstance(data, list):
        return []

    summaries: list[PullRequestSummary] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        summaries.append(
            PullRequestSummary(
                number=int(item.get("number", 0)),
                title=str(item.get("title", "Untitled")),
                author=_author_login(item),
                url=str(item.get("html_url", "")),
                branch=_pr_branch(item),
                state=str(item.get("state", "unknown")),
            )
        )
    return summaries


def _summarize_failed_runs(data: Any) -> list[FailedRunSummary]:
    items = data.get("items", []) if isinstance(data, dict) else []
    summaries: list[FailedRunSummary] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "Untitled"))
        summaries.append(
            FailedRunSummary(
                run_id=_ci_run_id(item),
                title=title,
                workflow_name=title,
                branch=_pr_branch(item) if item.get("head") else "unknown",
                author=_author_login(item),
                url=str(item.get("html_url", "")),
                updated_at=str(item.get("updated_at", "")),
            )
        )

    return summaries


def _search_ci_runs(settings: Settings, status: str, hours: int = 24) -> list[FailedRunSummary]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")
    query = f"repo:{settings.github_repo_full} is:pr status:{status} updated:>{since}"
    result = call_github_tool_sync(
        settings.github_token,
        "search_issues",
        {
            "query": query,
            "perPage": 30,
            "sort": "updated",
            "order": "desc",
        },
    )
    data = _parse_tool_json(result, "search_issues")
    return _summarize_failed_runs(data)


def fetch_open_pull_requests(settings: Settings) -> list[PullRequestSummary]:
    """Fetch open pull requests for the configured repository."""
    result = call_github_tool_sync(
        settings.github_token,
        "list_pull_requests",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "state": "open",
            "perPage": 30,
            "sort": "updated",
            "direction": "desc",
        },
    )
    data = _parse_tool_json(result, "list_pull_requests")
    return _summarize_pull_requests(data)


def fetch_failed_ci_runs(settings: Settings, hours: int = 24) -> list[FailedRunSummary]:
    """Fetch failed CI runs for the configured repository within the last N hours."""
    return _search_ci_runs(settings, "failure", hours=hours)


def fetch_successful_ci_runs(settings: Settings, hours: int = 24) -> list[FailedRunSummary]:
    """Fetch successful CI runs for the configured repository within the last N hours."""
    return _search_ci_runs(settings, "success", hours=hours)


def fetch_open_issue_count(settings: Settings) -> int:
    """Return the number of open issues in the configured repository."""
    result = call_github_tool_sync(
        settings.github_token,
        "list_issues",
        {
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "state": "open",
            "perPage": 100,
        },
    )
    data = _parse_tool_json(result, "list_issues")
    if isinstance(data, list):
        return len(data)
    return 0


def fetch_latest_release(settings: Settings) -> ReleaseSummary | None:
    """Fetch the latest release for the configured repository, if any."""
    try:
        result = call_github_tool_sync(
            settings.github_token,
            "get_latest_release",
            {
                "owner": settings.github_owner,
                "repo": settings.github_repo,
            },
        )
    except McpError as error:
        if "404" in str(error):
            return None
        raise GitHubFetchError(str(error)) from error

    if result.isError:
        message = extract_text_result(result).strip()
        if "404" in message:
            return None
        return None

    data = _parse_tool_json(result, "get_latest_release")
    if not isinstance(data, dict):
        return None

    author = data.get("author") or {}
    return ReleaseSummary(
        tag_name=str(data.get("tag_name", "")),
        name=str(data.get("name") or data.get("tag_name", "Release")),
        author=str(author.get("login", "unknown")),
        published_at=str(data.get("published_at", "")),
        url=str(data.get("html_url", "")),
    )


def fetch_github_data(settings: Settings) -> GitHubFetchResult:
    """Fetch open PRs and failed CI results for the configured repository."""
    raw: dict[str, Any] = {}
    errors: list[str] = []
    open_prs: list[PullRequestSummary] = []
    failed_runs: list[FailedRunSummary] = []

    try:
        open_prs = fetch_open_pull_requests(settings)
        raw["open_pull_requests"] = [asdict(pr) for pr in open_prs]
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"open PRs: {error}")
        raw["open_pull_requests"] = {"error": str(error)}

    try:
        failed_runs = fetch_failed_ci_runs(settings)
        raw["failed_ci"] = {"items": [asdict(run) for run in failed_runs]}
    except (GitHubFetchError, MCPConnectionError) as error:
        errors.append(f"failed CI: {error}")
        raw["failed_ci"] = {"error": str(error)}

    return GitHubFetchResult(
        repo=settings.github_repo_full,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        open_pull_requests=open_prs,
        failed_runs=failed_runs,
        raw=raw,
        errors=errors,
    )


def save_github_sample(result: GitHubFetchResult, path: Path | None = None) -> Path:
    """Write fetch results to logs/github_sample.json."""
    output_path = path or GITHUB_SAMPLE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "repo": result.repo,
        "fetched_at": result.fetched_at,
        "open_pull_requests": [asdict(pr) for pr in result.open_pull_requests],
        "failed_runs": [asdict(run) for run in result.failed_runs],
        "errors": result.errors,
        "raw": result.raw,
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def print_github_summary(result: GitHubFetchResult) -> None:
    """Print human-readable GitHub fetch summary."""
    print(f"Repository: {result.repo}")

    if result.errors:
        print("\nCould not fetch GitHub data. See warnings below.")
        print("This usually means your token cannot access the repo (private repo / missing PAT permissions).")
        for error in result.errors:
            print(f"- {error}")
        return

    print(f"Open PRs: {len(result.open_pull_requests)}")

    if result.open_pull_requests:
        print("\nOpen pull requests:")
        for pr in result.open_pull_requests:
            print(f"- #{pr.number} {pr.title} ({pr.author}, branch: {pr.branch})")
    else:
        print("No open pull requests.")

    print(f"\nFailed CI (last 24h): {len(result.failed_runs)}")
    if result.failed_runs:
        print("\nFailed runs:")
        for run in result.failed_runs:
            print(f"- {run.workflow_name} | author: {run.author} | branch: {run.branch} | {run.url}")
    else:
        print("No failed CI runs in the last 24 hours.")
