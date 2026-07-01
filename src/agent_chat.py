"""Natural language chat with OpenRouter and Firebase session memory (Step 11.3+)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from agent_loop import run_agent_loop
from app_logging import get_logger, log_workflow_end, log_workflow_start
from config import Settings
from firebase_store import get_session_messages, log_agent_run, save_message

logger = get_logger("agent_chat")

SYSTEM_PROMPT = """You are a helpful DevOps assistant for an MCP automation client.
The client monitors a GitHub repository and can send email alerts and digests.
You have tools to fetch live GitHub data, preview or send CI alerts, preview or send daily digests,
send test emails, and check pull request events.
Use tools when the user asks for live repository status or wants an action performed.
After tool results, summarize the outcome clearly for the user in plain language."""

DRY_RUN_PROMPT = """
Dry-run mode is ON. Use preview tools only (preview_daily_digest, run_ci_alert_preview, fetch_github_summary).
Do not send emails or live PR notifications."""


class AgentChatError(Exception):
    """Raised when the ask/chat workflow cannot run."""


@dataclass(frozen=True)
class AskResult:
    session_id: str
    response: str
    prior_message_count: int
    model: str
    tools_called: list[str]


def new_session_id() -> str:
    return f"session-{uuid.uuid4().hex[:12]}"


def _session_title(user_message: str) -> str:
    text = " ".join(user_message.split())
    if len(text) <= 80:
        return text
    return f"{text[:77]}..."


def _build_system_prompt(settings: Settings, *, dry_run: bool) -> str:
    prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"Configured repository: {settings.github_repo_full}."
    )
    if dry_run:
        prompt += DRY_RUN_PROMPT
    return prompt


def _to_llm_messages(stored_messages: list[dict]) -> list[dict[str, str]]:
    """Convert Firestore messages to OpenRouter chat format."""
    llm_messages: list[dict[str, str]] = []
    for message in stored_messages:
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            llm_messages.append({"role": role, "content": content})
    return llm_messages


def _save_tool_messages(
    settings: Settings,
    session_id: str,
    tools_called: list[str],
) -> None:
    if not tools_called:
        return
    for tool_name in tools_called:
        save_message(
            settings,
            session_id,
            "tool",
            f"Executed {tool_name}.",
            tool_name=tool_name,
        )


def run_ask(
    settings: Settings,
    user_message: str,
    *,
    session_id: str | None = None,
    dry_run: bool = False,
    auto_approve: bool = False,
) -> AskResult:
    """Run one agent turn with tool calling and Firebase session memory."""
    question = user_message.strip()
    if not question:
        raise AgentChatError("Ask a question, e.g. python src/main.py ask \"How many open PRs?\"")

    active_session = (session_id or "").strip() or new_session_id()
    is_new_session = not (session_id or "").strip()

    log_workflow_start(logger, "agent_ask", session_id=active_session, dry_run=dry_run)
    try:
        prior_messages = get_session_messages(settings, active_session, limit=50)
        llm_messages: list[dict[str, str]] = [
            {"role": "system", "content": _build_system_prompt(settings, dry_run=dry_run)}
        ]
        llm_messages.extend(_to_llm_messages(prior_messages))
        llm_messages.append({"role": "user", "content": question})

        save_message(
            settings,
            active_session,
            "user",
            question,
            title=_session_title(question) if is_new_session or not prior_messages else None,
        )

        loop_result = run_agent_loop(
            settings,
            llm_messages,
            max_iterations=settings.agent_max_tool_iterations,
            dry_run=dry_run,
            auto_approve=auto_approve,
            session_id=active_session,
        )

        _save_tool_messages(
            settings,
            active_session,
            loop_result.tools_called,
        )
        save_message(settings, active_session, "assistant", loop_result.response)

        log_agent_run(
            settings,
            session_id=active_session,
            model=loop_result.model,
            prompt_tokens=loop_result.prompt_tokens,
            completion_tokens=loop_result.completion_tokens,
            tools_called=loop_result.tools_called,
            success=True,
        )

        log_workflow_end(logger, "agent_ask", success=True, detail=active_session)
        return AskResult(
            session_id=active_session,
            response=loop_result.response,
            prior_message_count=len(prior_messages),
            model=loop_result.model,
            tools_called=loop_result.tools_called,
        )
    except Exception as error:
        log_agent_run(
            settings,
            session_id=active_session,
            model=settings.openrouter_model,
            prompt_tokens=0,
            completion_tokens=0,
            tools_called=[],
            success=False,
            error=str(error),
        )
        log_workflow_end(logger, "agent_ask", success=False, detail=str(error))
        raise
