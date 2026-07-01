"""Firebase Firestore storage for agent memory and history (Step 11.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

from app_logging import get_logger
from config import ROOT, Settings

logger = get_logger("firebase")

COLLECTION_SESSIONS = "agent_sessions"
COLLECTION_MESSAGES = "messages"
COLLECTION_AGENT_RUNS = "agent_runs"
COLLECTION_WORKFLOW_HISTORY = "workflow_history"
DEFAULT_CREDENTIALS_PATH = ROOT / "config" / "firebase-service-account.json"


class FirebaseStoreError(Exception):
    """Raised when Firestore cannot be initialized or used."""


def _resolve_credentials_path(settings: Settings) -> Path:
    raw = settings.firebase_credentials_path or DEFAULT_CREDENTIALS_PATH
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _require_firebase_config(settings: Settings) -> tuple[str, Path]:
    project_id = (settings.firebase_project_id or "").strip()
    if not project_id:
        raise FirebaseStoreError(
            "Missing FIREBASE_PROJECT_ID in .env. "
            "Find it in Firebase Console → Project settings."
        )

    cred_path = _resolve_credentials_path(settings)
    if not cred_path.exists():
        raise FirebaseStoreError(
            f"Firebase credentials file not found: {cred_path}\n"
            "Download a service account key from Firebase Console → "
            "Project settings → Service accounts → Generate new private key."
        )
    return project_id, cred_path


def init_firebase(settings: Settings) -> firestore.Client:
    """Connect to Firestore once per process using the service account."""
    project_id, cred_path = _require_firebase_config(settings)

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred, {"projectId": project_id})
        logger.info("firebase_initialized project_id=%s", project_id)

    return firestore.client()


def _ensure_session(
    db: firestore.Client,
    session_id: str,
    *,
    title: str | None = None,
) -> firestore.DocumentReference:
    session_ref = db.collection(COLLECTION_SESSIONS).document(session_id)
    snapshot = session_ref.get()
    if not snapshot.exists:
        session_ref.set(
            {
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "title": title or session_id,
            }
        )
    else:
        updates: dict[str, Any] = {"updated_at": firestore.SERVER_TIMESTAMP}
        if title:
            updates["title"] = title
        session_ref.update(updates)
    return session_ref


def save_message(
    settings: Settings,
    session_id: str,
    role: str,
    content: str,
    *,
    tool_name: str | None = None,
    tool_result: dict[str, Any] | None = None,
    title: str | None = None,
) -> str:
    """Save a chat message under agent_sessions/{sessionId}/messages."""
    db = init_firebase(settings)
    session_ref = _ensure_session(db, session_id, title=title)

    message_ref = session_ref.collection(COLLECTION_MESSAGES).document()
    message_ref.set(
        {
            "role": role,
            "content": content,
            "tool_name": tool_name,
            "tool_result": tool_result,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("firebase_message_saved session_id=%s role=%s", session_id, role)
    return message_ref.id


def get_session_messages(
    settings: Settings,
    session_id: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Load messages for a session ordered by created_at."""
    db = init_firebase(settings)
    query = (
        db.collection(COLLECTION_SESSIONS)
        .document(session_id)
        .collection(COLLECTION_MESSAGES)
        .order_by("created_at")
        .limit(limit)
    )

    messages: list[dict[str, Any]] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        messages.append(data)
    return messages


def log_agent_run(
    settings: Settings,
    *,
    session_id: str | None = None,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    tools_called: list[str],
    success: bool,
    error: str | None = None,
    llm_calls: int = 0,
    latency_ms: float = 0.0,
) -> str:
    """Record an LLM agent run in agent_runs."""
    db = init_firebase(settings)
    run_ref = db.collection(COLLECTION_AGENT_RUNS).document()
    run_ref.set(
        {
            "session_id": session_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tools_called": tools_called,
            "llm_calls": llm_calls,
            "latency_ms": round(latency_ms, 1),
            "success": success,
            "error": error,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info(
        "firebase_agent_run_logged run_id=%s success=%s latency_ms=%.0f llm_calls=%s",
        run_ref.id,
        success,
        latency_ms,
        llm_calls,
    )
    return run_ref.id


def log_workflow_history(
    settings: Settings,
    *,
    workflow: str,
    status: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Record workflow execution history in workflow_history."""
    db = init_firebase(settings)
    entry_ref = db.collection(COLLECTION_WORKFLOW_HISTORY).document()
    entry_ref.set(
        {
            "workflow": workflow,
            "status": status,
            "summary": summary,
            "metadata": metadata or {},
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("firebase_workflow_history_logged workflow=%s status=%s", workflow, status)
    return entry_ref.id


def run_firebase_connectivity_test(settings: Settings) -> dict[str, Any]:
    """Write and read test documents to verify Firestore connectivity."""
    session_id = f"firebase-test-{uuid.uuid4().hex[:8]}"
    test_content = "MCP client Firebase test OK"

    message_id = save_message(
        settings,
        session_id,
        "user",
        test_content,
        title="Firebase connectivity test",
    )
    messages = get_session_messages(settings, session_id, limit=5)
    latest = next((msg for msg in messages if msg.get("id") == message_id), None)
    if not latest or latest.get("content") != test_content:
        raise FirebaseStoreError("Firestore read-back failed for test message.")

    run_id = log_agent_run(
        settings,
        session_id=session_id,
        model="firebase-test",
        prompt_tokens=0,
        completion_tokens=0,
        tools_called=[],
        success=True,
    )
    history_id = log_workflow_history(
        settings,
        workflow="firebase_test",
        status="success",
        summary=test_content,
        metadata={"session_id": session_id, "message_id": message_id},
    )

    return {
        "project_id": settings.firebase_project_id,
        "session_id": session_id,
        "message_id": message_id,
        "run_id": run_id,
        "history_id": history_id,
        "message_count": len(messages),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def _format_timestamp(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if hasattr(value, "timestamp"):
        return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc).isoformat()
    return str(value)


def _doc_to_dict(doc: Any) -> dict[str, Any]:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    if "created_at" in data:
        data["created_at"] = _format_timestamp(data["created_at"])
    if "updated_at" in data:
        data["updated_at"] = _format_timestamp(data["updated_at"])
    return data


def list_recent_sessions(
    settings: Settings,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List agent sessions ordered by most recently updated."""
    db = init_firebase(settings)
    query = (
        db.collection(COLLECTION_SESSIONS)
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    return [_doc_to_dict(doc) for doc in query.stream()]


def list_recent_agent_runs(
    settings: Settings,
    *,
    limit: int = 20,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """List agent runs ordered by most recent, optionally filtered by session."""
    db = init_firebase(settings)
    query = db.collection(COLLECTION_AGENT_RUNS).order_by(
        "created_at", direction=firestore.Query.DESCENDING
    )
    if session_id:
        query = query.where("session_id", "==", session_id)
    query = query.limit(limit)
    return [_doc_to_dict(doc) for doc in query.stream()]


def list_recent_workflow_history(
    settings: Settings,
    *,
    limit: int = 20,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """List workflow history entries, optionally filtered by session in metadata."""
    db = init_firebase(settings)
    fetch_limit = limit * 5 if session_id else limit
    query = (
        db.collection(COLLECTION_WORKFLOW_HISTORY)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(fetch_limit)
    )
    entries = [_doc_to_dict(doc) for doc in query.stream()]
    if session_id:
        entries = [
            entry
            for entry in entries
            if (entry.get("metadata") or {}).get("session_id") == session_id
        ]
    return entries[:limit]


def get_session(settings: Settings, session_id: str) -> dict[str, Any] | None:
    """Return session document metadata or None if missing."""
    db = init_firebase(settings)
    snapshot = db.collection(COLLECTION_SESSIONS).document(session_id).get()
    if not snapshot.exists:
        return None
    return _doc_to_dict(snapshot)
