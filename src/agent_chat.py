"""Natural language chat with OpenRouter and Firebase session memory (Step 11.3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app_logging import get_logger, log_workflow_end, log_workflow_start
from config import Settings
from firebase_store import get_session_messages, log_agent_run, save_message
from llm_client import chat_completion

logger = get_logger("agent_chat")

SYSTEM_PROMPT = """You are a helpful DevOps assistant for an MCP automation client.
The client monitors a GitHub repository and can send email alerts and digests.
Answer clearly and concisely. If you do not have live repository data yet, say so.
Tool calling is not available in this mode yet — answer from general knowledge and chat context only."""


class AgentChatError(Exception):
    """Raised when the ask/chat workflow cannot run."""


@dataclass(frozen=True)
class AskResult:
    session_id: str
    response: str
    prior_message_count: int
    model: str


def new_session_id() -> str:
    return f"session-{uuid.uuid4().hex[:12]}"


def _session_title(user_message: str) -> str:
    text = " ".join(user_message.split())
    if len(text) <= 80:
        return text
    return f"{text[:77]}..."


def _to_llm_messages(stored_messages: list[dict]) -> list[dict[str, str]]:
    """Convert Firestore messages to OpenRouter chat format."""
    llm_messages: list[dict[str, str]] = []
    for message in stored_messages:
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            llm_messages.append({"role": role, "content": content})
    return llm_messages


def run_ask(
    settings: Settings,
    user_message: str,
    *,
    session_id: str | None = None,
) -> AskResult:
    """Run one chat turn: load history, call LLM, persist messages to Firestore."""
    question = user_message.strip()
    if not question:
        raise AgentChatError("Ask a question, e.g. python src/main.py ask \"How many open PRs?\"")

    active_session = (session_id or "").strip() or new_session_id()
    is_new_session = not (session_id or "").strip()

    log_workflow_start(logger, "agent_ask", session_id=active_session)
    try:
        prior_messages = get_session_messages(settings, active_session, limit=50)
        llm_messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        llm_messages.extend(_to_llm_messages(prior_messages))
        llm_messages.append({"role": "user", "content": question})

        save_message(
            settings,
            active_session,
            "user",
            question,
            title=_session_title(question) if is_new_session or not prior_messages else None,
        )

        completion = chat_completion(settings, llm_messages)

        save_message(settings, active_session, "assistant", completion.content)

        log_agent_run(
            settings,
            session_id=active_session,
            model=completion.model,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            tools_called=[],
            success=True,
        )

        log_workflow_end(logger, "agent_ask", success=True, detail=active_session)
        return AskResult(
            session_id=active_session,
            response=completion.content,
            prior_message_count=len(prior_messages),
            model=completion.model,
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
