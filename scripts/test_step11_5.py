#!/usr/bin/env python3
"""Step 11.5 — verify agent tool-calling loop."""

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
    print("Step 11.5 — Agent Loop Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/agent_loop.py exists", (ROOT / "src" / "agent_loop.py").is_file()))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ask", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("ask --dry-run available", "--dry-run" in help_run.stdout))

    try:
        from agent_loop import (
            AgentLoopError,
            _resolve_tool_name,
            run_agent_loop,
        )
        from config import load_settings
        from llm_client import ChatResult

        results.append(check("dry-run remaps digest send", _resolve_tool_name("send_daily_digest", dry_run=True) == "preview_daily_digest"))
        results.append(check("dry-run blocks test email", _resolve_tool_name("send_test_email", dry_run=True) is None))

        settings = load_settings()
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "fetch_github_summary",
                "arguments": "{}",
            },
        }
        final_completion = ChatResult(
            content="You have 2 open PRs and no failed CI runs.",
            model="openrouter/free",
            prompt_tokens=20,
            completion_tokens=10,
            tool_calls=[],
            assistant_message={"role": "assistant", "content": "You have 2 open PRs and no failed CI runs."},
        )
        tool_completion = ChatResult(
            content="",
            model="openrouter/free",
            prompt_tokens=15,
            completion_tokens=0,
            tool_calls=[tool_call],
            assistant_message={
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call],
            },
        )

        with (
            patch("agent_loop.chat_completion", side_effect=[tool_completion, final_completion]),
            patch(
                "agent_loop.execute_agent_tool",
                return_value={
                    "tool": "fetch_github_summary",
                    "success": True,
                    "summary": "Fetched shelarrohit45/MCP-Client: 2 open PR(s), 0 failed CI run(s).",
                    "data": {"open_pull_requests": [{}, {}]},
                },
            ),
        ):
            result = run_agent_loop(
                settings,
                [{"role": "system", "content": "test"}, {"role": "user", "content": "How many open PRs?"}],
            )
            results.append(check("agent loop returns final text", "2 open PRs" in result.response))
            results.append(check("agent loop records tools_called", result.tools_called == ["fetch_github_summary"]))
            results.append(check("agent loop uses multiple iterations", result.iterations == 2))

        with (
            patch("agent_loop.chat_completion", return_value=tool_completion),
            patch(
                "agent_loop._execute_loop_tool",
                return_value={"tool": "fetch_github_summary", "success": True, "summary": "ok"},
            ),
        ):
            try:
                run_agent_loop(
                    settings,
                    [{"role": "user", "content": "loop forever"}],
                    max_iterations=1,
                )
                results.append(check("max iterations raises AgentLoopError", False))
            except AgentLoopError:
                results.append(check("max iterations raises AgentLoopError", True))
    except Exception as error:
        results.append(check("agent_loop unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nTry live agent commands:")
        print('  python src/main.py ask "Check CI failures and tell me what you find"')
        print('  python src/main.py ask --dry-run "What would the digest contain?"')
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
