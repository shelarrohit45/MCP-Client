"""Agent loop: LLM tool calling with workflow execution (Step 11.5)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agent_guardrails import confirm_sensitive_tool, denied_tool_result, is_sensitive_tool
from agent_tools import execute_agent_tool, tool_schemas
from app_logging import get_logger
from config import Settings
from llm_client import LLMClientError, chat_completion, parse_tool_arguments

logger = get_logger("agent_loop")

DEFAULT_MAX_TOOL_ITERATIONS = 5

DRY_RUN_TOOL_REMAP: dict[str, str] = {
    "send_daily_digest": "preview_daily_digest",
    "run_ci_alert": "run_ci_alert_preview",
}

DRY_RUN_BLOCKED_TOOLS = frozenset({"send_test_email", "check_pr_events"})


class AgentLoopError(Exception):
    """Raised when the agent loop cannot complete."""


@dataclass(frozen=True)
class AgentLoopResult:
    response: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    tools_called: list[str]
    iterations: int
    latency_ms: float


def _resolve_tool_name(tool_name: str, *, dry_run: bool) -> str | None:
    if not dry_run:
        return tool_name
    if tool_name in DRY_RUN_BLOCKED_TOOLS:
        return None
    return DRY_RUN_TOOL_REMAP.get(tool_name, tool_name)


def _execute_loop_tool(
    settings: Settings,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    dry_run: bool,
    auto_approve: bool,
    session_id: str | None,
) -> dict[str, Any]:
    resolved = _resolve_tool_name(tool_name, dry_run=dry_run)
    if resolved is None:
        return {
            "tool": tool_name,
            "success": False,
            "summary": f"Tool '{tool_name}' is blocked in dry-run mode.",
            "error": "dry_run_blocked",
        }

    if not dry_run and is_sensitive_tool(resolved):
        if not confirm_sensitive_tool(
            settings,
            resolved,
            auto_approve=auto_approve,
            session_id=session_id,
            require_confirmation=settings.agent_require_confirmation,
        ):
            return denied_tool_result(resolved)

    return execute_agent_tool(settings, resolved, arguments)


def _tool_result_content(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=True)


def run_agent_loop(
    settings: Settings,
    messages: list[dict[str, Any]],
    *,
    max_iterations: int | None = None,
    dry_run: bool = False,
    auto_approve: bool = False,
    session_id: str | None = None,
) -> AgentLoopResult:
    """Run think → tool call → observe until the model returns a final answer."""
    limit = max_iterations or getattr(settings, "agent_max_tool_iterations", DEFAULT_MAX_TOOL_ITERATIONS)
    tools = tool_schemas()
    conversation = list(messages)

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_latency_ms = 0.0
    tools_called: list[str] = []
    resolved_model = settings.openrouter_model
    iterations = 0

    for _ in range(limit):
        iterations += 1
        completion = chat_completion(settings, conversation, tools=tools)
        total_prompt_tokens += completion.prompt_tokens
        total_completion_tokens += completion.completion_tokens
        total_latency_ms += completion.latency_ms
        resolved_model = completion.model

        if not completion.tool_calls:
            if not completion.content:
                raise AgentLoopError("Model returned neither text nor tool calls.")
            return AgentLoopResult(
                response=completion.content,
                model=resolved_model,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                tools_called=tools_called,
                iterations=iterations,
                latency_ms=total_latency_ms,
            )

        conversation.append(completion.assistant_message)

        for tool_call in completion.tool_calls:
            function = tool_call.get("function") or {}
            tool_name = str(function.get("name", "")).strip()
            if not tool_name:
                continue

            arguments = parse_tool_arguments(function.get("arguments"))
            logger.info("agent_tool_call tool=%s dry_run=%s", tool_name, dry_run)
            result = _execute_loop_tool(
                settings,
                tool_name,
                arguments,
                dry_run=dry_run,
                auto_approve=auto_approve,
                session_id=session_id,
            )
            tools_called.append(tool_name)

            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": str(tool_call.get("id", "")),
                    "content": _tool_result_content(result),
                }
            )

    raise AgentLoopError(
        f"Agent exceeded the maximum of {limit} tool iteration(s) without a final answer."
    )
