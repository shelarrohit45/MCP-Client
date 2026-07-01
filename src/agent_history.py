"""CLI display for agent observability from Firestore (Step 11.7)."""

from __future__ import annotations

from config import Settings
from firebase_store import (
    get_session,
    get_session_messages,
    list_recent_agent_runs,
    list_recent_sessions,
    list_recent_workflow_history,
)

DEFAULT_LIMIT = 20


def _truncate(text: str, max_len: int = 72) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 3]}..."


def _tools_label(tools: list[str] | None) -> str:
    if not tools:
        return "-"
    return ", ".join(tools)


def _print_session_overview(settings: Settings, session_id: str, *, limit: int) -> None:
    session = get_session(settings, session_id)
    if not session:
        print(f"Session not found: {session_id}")
        return

    print(f"=== Session: {session_id} ===")
    print(f"Title:   {session.get('title', '-')}")
    print(f"Created: {session.get('created_at', '-')}")
    print(f"Updated: {session.get('updated_at', '-')}")
    print()

    messages = get_session_messages(settings, session_id, limit=limit)
    print(f"--- Messages ({len(messages)}) ---")
    if not messages:
        print("(no messages)")
    else:
        for message in messages:
            role = str(message.get("role", "?"))
            content = _truncate(str(message.get("content", "")))
            tool_name = message.get("tool_name")
            suffix = f" [tool={tool_name}]" if tool_name else ""
            print(f"[{role}]{suffix} {content}")
    print()

    runs = list_recent_agent_runs(settings, limit=limit, session_id=session_id)
    print(f"--- Agent Runs ({len(runs)}) ---")
    if not runs:
        print("(no runs)")
    else:
        for run in runs:
            status = "ok" if run.get("success") else "failed"
            tools = _tools_label(run.get("tools_called"))
            tokens = int(run.get("prompt_tokens", 0) or 0) + int(run.get("completion_tokens", 0) or 0)
            latency = run.get("latency_ms", 0) or 0
            print(
                f"{run.get('created_at', '-')} | {run.get('model', '-')} | "
                f"{tokens} tok | {latency}ms | {status} | tools: {tools}"
            )
            if run.get("error"):
                print(f"  error: {run['error']}")
    print()

    history = list_recent_workflow_history(settings, limit=limit, session_id=session_id)
    print(f"--- Workflow / Tool Activity ({len(history)}) ---")
    if not history:
        print("(no workflow history)")
    else:
        for entry in history:
            print(
                f"{entry.get('created_at', '-')} | {entry.get('workflow', '-')} | "
                f"{entry.get('status', '-')} | {_truncate(str(entry.get('summary', '')))}"
            )


def _print_global_overview(settings: Settings, *, limit: int) -> None:
    sessions = list_recent_sessions(settings, limit=limit)
    print(f"=== Recent Sessions ({len(sessions)}) ===")
    if not sessions:
        print("(no sessions)")
    else:
        for session in sessions:
            print(
                f"{session.get('id', '-')} | {session.get('updated_at', '-')} | "
                f"{_truncate(str(session.get('title', '-')))}"
            )
    print()

    runs = list_recent_agent_runs(settings, limit=limit)
    print(f"=== Recent Agent Runs ({len(runs)}) ===")
    if not runs:
        print("(no runs)")
    else:
        for run in runs:
            status = "ok" if run.get("success") else "failed"
            tools = _tools_label(run.get("tools_called"))
            tokens = int(run.get("prompt_tokens", 0) or 0) + int(run.get("completion_tokens", 0) or 0)
            latency = run.get("latency_ms", 0) or 0
            print(
                f"{run.get('created_at', '-')} | {run.get('session_id', '-')} | "
                f"{run.get('model', '-')} | {tokens} tok | {latency}ms | {status} | tools: {tools}"
            )
    print()

    history = list_recent_workflow_history(settings, limit=limit)
    print(f"=== Recent Workflow Activity ({len(history)}) ===")
    if not history:
        print("(no workflow history)")
    else:
        for entry in history:
            metadata = entry.get("metadata") or {}
            session_hint = metadata.get("session_id") or "-"
            print(
                f"{entry.get('created_at', '-')} | {entry.get('workflow', '-')} | "
                f"{entry.get('status', '-')} | session={session_hint} | "
                f"{_truncate(str(entry.get('summary', '')))}"
            )


def print_agent_history(
    settings: Settings,
    *,
    session_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> None:
    """Print agent sessions, runs, and workflow history from Firestore."""
    if session_id:
        _print_session_overview(settings, session_id, limit=limit)
    else:
        _print_global_overview(settings, limit=limit)
