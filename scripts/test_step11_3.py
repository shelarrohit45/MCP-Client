#!/usr/bin/env python3
"""Step 11.3 — verify natural language ask command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 11.3 — Natural Language Ask Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/agent_chat.py exists", (ROOT / "src" / "agent_chat.py").is_file()))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ask", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("ask command registered", help_run.returncode == 0))
    results.append(check("ask --session flag documented", "--session" in help_run.stdout))
    results.append(check("ask --dry-run flag documented", "--dry-run" in help_run.stdout))

    try:
        from agent_chat import (
            AgentChatError,
            _to_llm_messages,
            new_session_id,
            run_ask,
        )
        from agent_loop import AgentLoopResult
        from config import load_settings

        session_id = new_session_id()
        results.append(check("new_session_id format", session_id.startswith("session-")))

        converted = _to_llm_messages(
            [
                {"role": "user", "content": "hello"},
                {"role": "tool", "content": "ignored"},
                {"role": "assistant", "content": "hi"},
            ]
        )
        results.append(check("_to_llm_messages filters roles", len(converted) == 2))

        settings = load_settings()
        with (
            patch("agent_chat.get_session_messages", return_value=[]),
            patch("agent_chat.save_message", return_value="msg-1"),
            patch(
                "agent_chat.run_agent_loop",
                return_value=AgentLoopResult(
                    response="Repo looks healthy.",
                    model="openrouter/free",
                    prompt_tokens=12,
                    completion_tokens=6,
                    tools_called=["fetch_github_summary"],
                    iterations=2,
                    latency_ms=150.0,
                ),
            ),
            patch("agent_chat.log_agent_run", return_value="run-1"),
        ):
            result = run_ask(settings, "How is my repo?", session_id=session_id)
            results.append(check("run_ask returns response", result.response == "Repo looks healthy."))
            results.append(check("run_ask keeps session id", result.session_id == session_id))
            results.append(check("run_ask reports tools_called", "fetch_github_summary" in result.tools_called))

        try:
            run_ask(settings, "   ")
            results.append(check("empty question raises AgentChatError", False))
        except AgentChatError:
            results.append(check("empty question raises AgentChatError", True))
    except Exception as error:
        results.append(check("agent_chat unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nTry a live chat:")
        print('  python src/main.py ask "What does this MCP client do?"')
        print('  python src/main.py ask --session <session-id> "Follow up question"')
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
