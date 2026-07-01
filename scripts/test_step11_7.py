#!/usr/bin/env python3
"""Step 11.7 — verify agent observability and agent-history CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 11.7 — Agent Observability Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"
    app_logging = (ROOT / "src" / "app_logging.py").read_text(encoding="utf-8")
    firebase_store = (ROOT / "src" / "firebase_store.py").read_text(encoding="utf-8")
    llm_client = (ROOT / "src" / "llm_client.py").read_text(encoding="utf-8")

    results.append(check("src/agent_history.py exists", (ROOT / "src" / "agent_history.py").is_file()))
    results.append(check("log_llm_call in app_logging.py", "def log_llm_call" in app_logging))
    results.append(check("latency_ms in log_agent_run", "latency_ms" in firebase_store))
    results.append(check("list_recent_agent_runs helper", "def list_recent_agent_runs" in firebase_store))
    results.append(check("list_recent_sessions helper", "def list_recent_sessions" in firebase_store))
    results.append(check("llm_client logs latency", "log_llm_call" in llm_client and "latency_ms" in llm_client))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "agent-history", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("agent-history command registered", help_run.returncode == 0))
    results.append(check("agent-history --session flag", "--session" in help_run.stdout))

    try:
        from dataclasses import replace

        from agent_history import print_agent_history
        from app_logging import log_llm_call
        from config import load_settings
        from firebase_store import (
            list_recent_agent_runs,
            list_recent_sessions,
            list_recent_workflow_history,
        )

        settings = load_settings()
        fake_settings = replace(
            settings,
            firebase_project_id="test-project",
            firebase_credentials_path=ROOT / "config" / "firebase-service-account.json",
        )

        mock_logger = MagicMock()
        log_llm_call(
            mock_logger,
            model="openrouter/free",
            latency_ms=123.4,
            prompt_tokens=10,
            completion_tokens=5,
            tool_calls=1,
        )
        results.append(check("log_llm_call writes structured log", mock_logger.info.called))

        mock_run_doc = MagicMock()
        mock_run_doc.id = "run-1"
        mock_run_doc.to_dict.return_value = {
            "session_id": "session-abc",
            "model": "openrouter/free",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "tools_called": ["fetch_github_summary"],
            "llm_calls": 2,
            "latency_ms": 250.0,
            "success": True,
            "created_at": None,
        }

        mock_session_doc = MagicMock()
        mock_session_doc.id = "session-abc"
        mock_session_doc.to_dict.return_value = {
            "title": "How many PRs?",
            "created_at": None,
            "updated_at": None,
        }

        mock_history_doc = MagicMock()
        mock_history_doc.id = "hist-1"
        mock_history_doc.to_dict.return_value = {
            "workflow": "agent_tool",
            "status": "success",
            "summary": "Fetched GitHub summary",
            "metadata": {"session_id": "session-abc"},
            "created_at": None,
        }

        mock_db = MagicMock()
        mock_runs_query = MagicMock()
        mock_runs_query.stream.return_value = [mock_run_doc]
        mock_sessions_query = MagicMock()
        mock_sessions_query.stream.return_value = [mock_session_doc]
        mock_history_query = MagicMock()
        mock_history_query.stream.return_value = [mock_history_doc]

        def collection_side_effect(name: str) -> MagicMock:
            coll = MagicMock()
            if name == "agent_runs":
                coll.order_by.return_value.limit.return_value = mock_runs_query
                coll.order_by.return_value.where.return_value.limit.return_value = mock_runs_query
            elif name == "agent_sessions":
                coll.order_by.return_value.limit.return_value = mock_sessions_query
                coll.document.return_value.get.return_value.exists = True
                coll.document.return_value.get.return_value.to_dict.return_value = (
                    mock_session_doc.to_dict.return_value
                )
                coll.document.return_value.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = []
            elif name == "workflow_history":
                coll.order_by.return_value.limit.return_value = mock_history_query
            return coll

        mock_db.collection.side_effect = collection_side_effect

        with patch("firebase_store.init_firebase", return_value=mock_db):
            sessions = list_recent_sessions(fake_settings, limit=5)
            runs = list_recent_agent_runs(fake_settings, limit=5)
            history = list_recent_workflow_history(fake_settings, limit=5, session_id="session-abc")
            results.append(check("list_recent_sessions returns docs", len(sessions) == 1))
            results.append(check("list_recent_agent_runs returns docs", len(runs) == 1))
            results.append(check("list_recent_workflow_history filters session", len(history) == 1))

            import io
            from contextlib import redirect_stdout

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                print_agent_history(fake_settings, session_id="session-abc", limit=5)
            output = buffer.getvalue()
            results.append(check("session view prints messages section", "--- Messages" in output))
            results.append(check("session view prints runs section", "--- Agent Runs" in output))
    except Exception as error:
        results.append(check("agent observability unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nNext: run agent-history against live Firestore:")
        print("  python src/main.py agent-history")
        print("  python src/main.py agent-history --session <id>")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
