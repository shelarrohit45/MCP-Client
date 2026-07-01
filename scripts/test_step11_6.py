#!/usr/bin/env python3
"""Step 11.6 — verify agent guardrails and confirmation."""

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
    print("Step 11.6 — Agent Guardrails Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/agent_guardrails.py exists", (ROOT / "src" / "agent_guardrails.py").is_file()))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ask", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("ask --yes flag documented", "--yes" in help_run.stdout))

    try:
        from agent_guardrails import (
            confirm_sensitive_tool,
            denied_tool_result,
            is_sensitive_tool,
        )
        from agent_loop import _execute_loop_tool
        from config import load_settings

        results.append(check("send_daily_digest is sensitive", is_sensitive_tool("send_daily_digest")))
        results.append(check("fetch_github_summary not sensitive", not is_sensitive_tool("fetch_github_summary")))

        settings = load_settings()
        with patch("agent_guardrails._log_confirmation") as mock_log:
            approved = confirm_sensitive_tool(
                settings,
                "send_daily_digest",
                auto_approve=True,
                session_id="session-test",
            )
            results.append(check("auto_approve skips prompt", approved is True))
            results.append(check("auto_approve logs confirmation", mock_log.called))

        with (
            patch("agent_guardrails._preview_sensitive_tool", return_value={"summary": "2 open PRs"}),
            patch("agent_guardrails.prompt_user_confirmation", return_value=False),
            patch("agent_guardrails._log_confirmation"),
        ):
            approved = confirm_sensitive_tool(
                settings,
                "run_ci_alert",
                session_id="session-test",
            )
            results.append(check("denied confirmation returns False", approved is False))

        denied = denied_tool_result("send_test_email")
        results.append(check("denied_tool_result has error code", denied.get("error") == "confirmation_denied"))

        with (
            patch("agent_loop.confirm_sensitive_tool", return_value=False),
            patch("agent_loop.execute_agent_tool") as mock_execute,
        ):
            result = _execute_loop_tool(
                settings,
                "send_daily_digest",
                {},
                dry_run=False,
                auto_approve=False,
                session_id="session-test",
            )
            results.append(check("blocked tool does not execute", not mock_execute.called))
            results.append(check("blocked tool returns denial", result.get("error") == "confirmation_denied"))

        with (
            patch("agent_loop.confirm_sensitive_tool", return_value=True),
            patch(
                "agent_loop.execute_agent_tool",
                return_value={"tool": "send_daily_digest", "success": True, "summary": "sent"},
            ) as mock_execute,
        ):
            result = _execute_loop_tool(
                settings,
                "send_daily_digest",
                {},
                dry_run=False,
                auto_approve=False,
                session_id="session-test",
            )
            results.append(check("approved tool executes", mock_execute.called))
            results.append(check("approved tool succeeds", result.get("success") is True))
    except Exception as error:
        results.append(check("agent_guardrails unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nLive test (will prompt unless you pass --yes):")
        print('  python src/main.py ask "Send digest now"')
        print('  python src/main.py ask --yes "Send digest now"')
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
