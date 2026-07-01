#!/usr/bin/env python3
"""Step 11.4 — verify agent tool definitions."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

EXPECTED_TOOLS = [
    "fetch_github_summary",
    "run_ci_alert",
    "run_ci_alert_preview",
    "send_daily_digest",
    "preview_daily_digest",
    "send_test_email",
    "check_pr_events",
]


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 11.4 — Agent Tools Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/agent_tools.py exists", (ROOT / "src" / "agent_tools.py").is_file()))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "agent-tools", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("agent-tools command registered", help_run.returncode == 0))

    cli_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "agent-tools"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("agent-tools CLI runs", cli_run.returncode == 0))
    for tool_name in EXPECTED_TOOLS:
        results.append(check(f"CLI lists {tool_name}", tool_name in cli_run.stdout))

    json_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "agent-tools", "--json"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("agent-tools --json runs", json_run.returncode == 0))
    try:
        schemas = json.loads(json_run.stdout)
        schema_names = [item["function"]["name"] for item in schemas]
        results.append(check("tool schemas count", len(schema_names) == len(EXPECTED_TOOLS)))
        results.append(
            check(
                "tool schemas match expected names",
                schema_names == EXPECTED_TOOLS,
            )
        )
    except json.JSONDecodeError as error:
        results.append(check("tool schemas parse as JSON", False, str(error)))

    try:
        from agent_tools import execute_agent_tool, get_agent_tool
        from config import load_settings

        settings = load_settings()
        tool = get_agent_tool("fetch_github_summary")
        results.append(check("get_agent_tool works", tool.name == "fetch_github_summary"))

        try:
            get_agent_tool("missing_tool")
            results.append(check("unknown tool raises AgentToolError", False))
        except Exception as error:
            results.append(
                check(
                    "unknown tool raises AgentToolError",
                    error.__class__.__name__ == "AgentToolError",
                )
            )

        fake_result = {
            "tool": "fetch_github_summary",
            "success": True,
            "summary": "ok",
            "data": {"open_pull_requests": []},
        }
        with (
            patch("agent_tools.fetch_github_data") as mock_fetch,
            patch("agent_tools.log_workflow_history", return_value="history-1") as mock_log,
        ):
            from github_fetch import GitHubFetchResult

            mock_fetch.return_value = GitHubFetchResult(
                repo="owner/repo",
                fetched_at="2026-01-01T00:00:00+00:00",
                open_pull_requests=[],
                failed_runs=[],
                raw={},
                errors=[],
            )
            result = execute_agent_tool(settings, "fetch_github_summary")
            results.append(check("execute_agent_tool returns result", result["success"] is True))
            results.append(check("execute_agent_tool logs history", mock_log.called))
    except Exception as error:
        results.append(check("agent_tools unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nList tools:")
        print("  python src/main.py agent-tools")
        print("  python src/main.py agent-tools --json")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
