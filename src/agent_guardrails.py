"""Human confirmation guardrails for sensitive agent tools (Step 11.6)."""

from __future__ import annotations

from typing import Any

from agent_tools import execute_agent_tool
from app_logging import get_logger
from config import Settings
from firebase_store import FirebaseStoreError, log_workflow_history

logger = get_logger("agent_guardrails")

SENSITIVE_TOOLS = frozenset(
    {
        "send_daily_digest",
        "run_ci_alert",
        "send_test_email",
        "check_pr_events",
    }
)

PREVIEW_TOOL_FOR_SENSITIVE: dict[str, str] = {
    "send_daily_digest": "preview_daily_digest",
    "run_ci_alert": "run_ci_alert_preview",
}


class AgentGuardrailError(Exception):
    """Raised when guardrail handling fails."""


def is_sensitive_tool(tool_name: str) -> bool:
    return tool_name in SENSITIVE_TOOLS


def _log_confirmation(
    settings: Settings,
    *,
    tool_name: str,
    approved: bool,
    session_id: str | None,
    note: str = "",
    preview_summary: str = "",
) -> None:
    status = "approved" if approved else "denied"
    summary = f"Confirmation {status} for tool '{tool_name}'."
    if note:
        summary = f"{summary} {note}"
    if preview_summary:
        summary = f"{summary} Preview: {preview_summary}"

    try:
        log_workflow_history(
            settings,
            workflow="agent_confirmation",
            status=status,
            summary=summary,
            metadata={
                "tool": tool_name,
                "approved": approved,
                "session_id": session_id,
                "note": note,
            },
        )
    except FirebaseStoreError as error:
        logger.warning("confirmation_log_failed tool=%s detail=%s", tool_name, error)


def _describe_sensitive_action(settings: Settings, tool_name: str) -> str:
    recipients = ", ".join(settings.email_recipients)
    descriptions = {
        "send_daily_digest": (
            f"Send the daily repository digest email to: {recipients}"
        ),
        "run_ci_alert": (
            f"Send CI failure alert email(s) to: {recipients}"
        ),
        "send_test_email": (
            f"Send a test email from {settings.email_sender} to: {recipients}"
        ),
        "check_pr_events": (
            f"Check pull request events and send notification email(s) to: {recipients}"
        ),
    }
    return descriptions.get(tool_name, f"Run sensitive tool '{tool_name}'.")


def _preview_sensitive_tool(settings: Settings, tool_name: str) -> dict[str, Any] | None:
    preview_tool = PREVIEW_TOOL_FOR_SENSITIVE.get(tool_name)
    if not preview_tool:
        return None
    return execute_agent_tool(settings, preview_tool)


def format_confirmation_prompt(
    settings: Settings,
    tool_name: str,
    preview_result: dict[str, Any] | None,
) -> str:
    lines = [
        "Sensitive action requested:",
        f"- Tool: {tool_name}",
        f"- Action: {_describe_sensitive_action(settings, tool_name)}",
    ]
    if preview_result and preview_result.get("summary"):
        lines.append(f"- Preview: {preview_result['summary']}")
    return "\n".join(lines)


def prompt_user_confirmation() -> bool:
    answer = input("Proceed? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def confirm_sensitive_tool(
    settings: Settings,
    tool_name: str,
    *,
    auto_approve: bool = False,
    session_id: str | None = None,
    require_confirmation: bool = True,
) -> bool:
    """Return True if a sensitive tool may run."""
    if not is_sensitive_tool(tool_name):
        return True

    if not require_confirmation:
        _log_confirmation(
            settings,
            tool_name=tool_name,
            approved=True,
            session_id=session_id,
            note="confirmation_disabled_in_config",
        )
        return True

    if auto_approve:
        _log_confirmation(
            settings,
            tool_name=tool_name,
            approved=True,
            session_id=session_id,
            note="auto_approved_via_flag",
        )
        return True

    preview_result = _preview_sensitive_tool(settings, tool_name)
    print(format_confirmation_prompt(settings, tool_name, preview_result))

    approved = prompt_user_confirmation()
    preview_summary = str((preview_result or {}).get("summary", ""))
    _log_confirmation(
        settings,
        tool_name=tool_name,
        approved=approved,
        session_id=session_id,
        preview_summary=preview_summary,
    )
    return approved


def denied_tool_result(tool_name: str) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "success": False,
        "summary": f"Action '{tool_name}' was not run because confirmation was denied.",
        "error": "confirmation_denied",
    }
