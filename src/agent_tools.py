"""Agent tools that wrap existing MCP workflows for LLM tool calling (Step 11.4)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from app_logging import get_logger
from config import Settings
from email_client import send_test_email
from firebase_store import FirebaseStoreError, log_workflow_history
from github_fetch import fetch_github_data
from workflows.ci_alert import run_ci_alert
from workflows.daily_digest import run_daily_digest
from workflows.pr_events import check_pr_events

logger = get_logger("agent_tools")


class AgentToolError(Exception):
    """Raised when an agent tool is unknown or cannot run."""


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, Any]
    workflow: str
    handler: Callable[[Settings], dict[str, Any]]


def _empty_object_schema() -> dict[str, Any]:
    return {"type": "object", "properties": {}, "required": []}


def _tool_result(
    *,
    tool_name: str,
    success: bool,
    summary: str,
    data: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": tool_name,
        "success": success,
        "summary": summary,
    }
    if data is not None:
        payload["data"] = data
    if error:
        payload["error"] = error
    return payload


def _log_tool_run(
    settings: Settings,
    *,
    workflow: str,
    status: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        log_workflow_history(
            settings,
            workflow=workflow,
            status=status,
            summary=summary,
            metadata=metadata,
        )
    except FirebaseStoreError as error:
        logger.warning("workflow_history_log_failed workflow=%s detail=%s", workflow, error)


def _handle_fetch_github_summary(settings: Settings) -> dict[str, Any]:
    result = fetch_github_data(settings)
    summary = (
        f"Fetched {settings.github_repo_full}: "
        f"{len(result.open_pull_requests)} open PR(s), "
        f"{len(result.failed_runs)} failed CI run(s) in last 24h."
    )
    if result.errors:
        summary += f" Warnings: {'; '.join(result.errors)}"
    return _tool_result(
        tool_name="fetch_github_summary",
        success=True,
        summary=summary,
        data={
            "repo": result.repo,
            "fetched_at": result.fetched_at,
            "open_pull_requests": [asdict(pr) for pr in result.open_pull_requests],
            "failed_runs": [asdict(run) for run in result.failed_runs],
            "errors": result.errors,
        },
    )


def _handle_run_ci_alert(settings: Settings) -> dict[str, Any]:
    result = run_ci_alert(settings, dry_run=False)
    if not result.failures:
        summary = "No CI failures found in the last 24 hours."
    elif result.sent:
        summary = f"Sent CI alert email for {len(result.failures)} failure(s)."
    else:
        summary = (
            f"Found {len(result.failures)} failure(s); "
            f"{result.skipped_duplicates} duplicate(s) skipped."
        )
    return _tool_result(
        tool_name="run_ci_alert",
        success=True,
        summary=summary,
        data={
            "repo": result.repo,
            "failure_count": len(result.failures),
            "sent": result.sent,
            "skipped_duplicates": result.skipped_duplicates,
            "failures": [asdict(failure) for failure in result.failures],
        },
    )


def _handle_run_ci_alert_preview(settings: Settings) -> dict[str, Any]:
    result = run_ci_alert(settings, dry_run=True)
    summary = (
        f"CI alert preview: {len(result.failures)} failure(s) would be included."
        if result.failures
        else "CI alert preview: no failures in the last 24 hours."
    )
    return _tool_result(
        tool_name="run_ci_alert_preview",
        success=True,
        summary=summary,
        data={
            "repo": result.repo,
            "failure_count": len(result.failures),
            "dry_run": True,
            "failures": [asdict(failure) for failure in result.failures],
        },
    )


def _handle_send_daily_digest(settings: Settings) -> dict[str, Any]:
    result = run_daily_digest(settings, send=True)
    data = result.data
    summary = (
        f"Daily digest sent for {data.repo}: "
        f"{len(data.open_prs)} open PR(s), {data.open_issue_count} open issue(s), "
        f"{len(data.failed_ci)} failed CI run(s) in last 24h."
    )
    return _tool_result(
        tool_name="send_daily_digest",
        success=True,
        summary=summary,
        data={
            "repo": data.repo,
            "date": data.date,
            "sent": result.sent,
            "open_pr_count": len(data.open_prs),
            "open_issue_count": data.open_issue_count,
            "failed_ci_count": len(data.failed_ci),
            "successful_ci_count": len(data.successful_ci),
            "errors": data.errors,
        },
    )


def _handle_preview_daily_digest(settings: Settings) -> dict[str, Any]:
    result = run_daily_digest(settings, dry_run=True)
    data = result.data
    summary = (
        f"Digest preview for {data.repo}: "
        f"{len(data.open_prs)} open PR(s), {data.open_issue_count} open issue(s)."
    )
    return _tool_result(
        tool_name="preview_daily_digest",
        success=True,
        summary=summary,
        data={
            "repo": data.repo,
            "date": data.date,
            "dry_run": True,
            "open_pr_count": len(data.open_prs),
            "open_issue_count": data.open_issue_count,
            "failed_ci_count": len(data.failed_ci),
            "successful_ci_count": len(data.successful_ci),
            "errors": data.errors,
        },
    )


def _handle_send_test_email(settings: Settings) -> dict[str, Any]:
    message = send_test_email(settings)
    summary = f"Test email sent from {settings.email_sender} to {', '.join(settings.email_recipients)}."
    return _tool_result(
        tool_name="send_test_email",
        success=True,
        summary=summary,
        data={"message": message, "recipients": settings.email_recipients},
    )


def _handle_check_pr_events(settings: Settings) -> dict[str, Any]:
    result = check_pr_events(settings, dry_run=False)
    summary = (
        f"Checked {result.checked} PR(s); sent {len(result.sent)} notification(s), "
        f"skipped {len(result.skipped)} duplicate(s)."
    )
    return _tool_result(
        tool_name="check_pr_events",
        success=True,
        summary=summary,
        data={
            "checked": result.checked,
            "sent": result.sent,
            "skipped": result.skipped,
        },
    )


def _build_tools() -> list[AgentTool]:
    return [
        AgentTool(
            name="fetch_github_summary",
            description="Fetch open pull requests and failed CI runs from GitHub for the configured repository.",
            parameters=_empty_object_schema(),
            workflow="fetch_github_summary",
            handler=_handle_fetch_github_summary,
        ),
        AgentTool(
            name="run_ci_alert",
            description="Send email alerts for new CI failures detected in the last 24 hours.",
            parameters=_empty_object_schema(),
            workflow="ci_alert",
            handler=_handle_run_ci_alert,
        ),
        AgentTool(
            name="run_ci_alert_preview",
            description="Preview CI failure alerts without sending email.",
            parameters=_empty_object_schema(),
            workflow="ci_alert_preview",
            handler=_handle_run_ci_alert_preview,
        ),
        AgentTool(
            name="send_daily_digest",
            description="Send the daily repository activity digest email to configured recipients.",
            parameters=_empty_object_schema(),
            workflow="daily_digest",
            handler=_handle_send_daily_digest,
        ),
        AgentTool(
            name="preview_daily_digest",
            description="Preview the daily digest content without sending email.",
            parameters=_empty_object_schema(),
            workflow="daily_digest_preview",
            handler=_handle_preview_daily_digest,
        ),
        AgentTool(
            name="send_test_email",
            description="Send a simple test email via the Email MCP integration.",
            parameters=_empty_object_schema(),
            workflow="send_test_email",
            handler=_handle_send_test_email,
        ),
        AgentTool(
            name="check_pr_events",
            description="Check pull request lifecycle events and send notification emails for new events.",
            parameters=_empty_object_schema(),
            workflow="pr_events",
            handler=_handle_check_pr_events,
        ),
    ]


_TOOLS_BY_NAME: dict[str, AgentTool] | None = None


def _tools_by_name() -> dict[str, AgentTool]:
    global _TOOLS_BY_NAME
    if _TOOLS_BY_NAME is None:
        _TOOLS_BY_NAME = {tool.name: tool for tool in _build_tools()}
    return _TOOLS_BY_NAME


def list_agent_tools() -> list[AgentTool]:
    """Return all registered agent tools."""
    return list(_tools_by_name().values())


def get_agent_tool(tool_name: str) -> AgentTool:
    tool = _tools_by_name().get(tool_name)
    if tool is None:
        known = ", ".join(sorted(_tools_by_name()))
        raise AgentToolError(f"Unknown agent tool '{tool_name}'. Known tools: {known}")
    return tool


def tool_schemas() -> list[dict[str, Any]]:
    """Return OpenAI/OpenRouter-compatible tool definitions."""
    schemas: list[dict[str, Any]] = []
    for tool in list_agent_tools():
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
        )
    return schemas


def execute_agent_tool(
    settings: Settings,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a tool by name and log the outcome to Firestore workflow history."""
    tool = get_agent_tool(tool_name)
    args = arguments or {}
    if args:
        logger.info("agent_tool_arguments_ignored tool=%s", tool_name)

    try:
        result = tool.handler(settings)
        _log_tool_run(
            settings,
            workflow=tool.workflow,
            status="success" if result.get("success") else "failure",
            summary=str(result.get("summary", "")),
            metadata={"tool": tool_name, "data": result.get("data")},
        )
        return result
    except Exception as error:
        message = str(error).strip() or error.__class__.__name__
        _log_tool_run(
            settings,
            workflow=tool.workflow,
            status="failure",
            summary=message,
            metadata={"tool": tool_name},
        )
        return _tool_result(
            tool_name=tool_name,
            success=False,
            summary=f"{tool_name} failed.",
            error=message,
        )


def format_tools_for_cli() -> str:
    """Human-readable list of tools for the agent-tools command."""
    lines = [f"Agent tools ({len(list_agent_tools())}):\n"]
    for tool in list_agent_tools():
        lines.append(f"- {tool.name}")
        lines.append(f"  {tool.description}")
        lines.append(f"  workflow: {tool.workflow}")
        lines.append("")
    return "\n".join(lines).strip()
