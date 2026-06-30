#!/usr/bin/env python3
"""Step 9 — verify logging and CI alert deduplication."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 9 — Logging + Dedup Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/app_logging.py exists", (ROOT / "src/app_logging.py").is_file()))
    results.append(check("src/workflow_state.py exists", (ROOT / "src/workflow_state.py").is_file()))
    results.append(check("src/error_messages.py exists", (ROOT / "src/error_messages.py").is_file()))

    try:
        from github_fetch import FailedRunSummary
        from workflow_state import WorkflowState, load_workflow_state, save_workflow_state
        from workflows.ci_alert import filter_new_failures

        failures = [
            FailedRunSummary(
                run_id="100:2026-06-30T10:00:00Z",
                title="PR A",
                workflow_name="PR A",
                branch="main",
                author="dev",
                url="https://example.com/1",
                updated_at="2026-06-30T10:00:00Z",
            ),
            FailedRunSummary(
                run_id="200:2026-06-30T11:00:00Z",
                title="PR B",
                workflow_name="PR B",
                branch="feat",
                author="dev",
                url="https://example.com/2",
                updated_at="2026-06-30T11:00:00Z",
            ),
        ]
        state = WorkflowState(alerted_run_ids={"100:2026-06-30T10:00:00Z"})
        new_failures, skipped = filter_new_failures(failures, state.alerted_run_ids)
        results.append(check("filter_new_failures skips alerted IDs", len(new_failures) == 1 and skipped == 1))

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state = WorkflowState()
            state.mark_alerted("abc123")
            save_workflow_state(state, state_path)
            loaded = load_workflow_state(state_path)
            results.append(check("state.json roundtrip", loaded.was_alerted("abc123")))
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            results.append(check("state.json shape", "alerted_run_ids" in payload and "last_ci_alert_at" in payload))
    except Exception as error:  # noqa: BLE001
        results.append(check("state/dedup unit tests", False, str(error)))

    dry_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ci-alert", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = dry_run.stdout + dry_run.stderr
    results.append(check("ci-alert --dry-run runs", dry_run.returncode == 0, output.strip()[:120]))

    app_log = ROOT / "logs" / "app.log"
    if app_log.exists():
        log_text = app_log.read_text(encoding="utf-8")
        results.append(check("logs/app.log records ci_alert run", "workflow=ci_alert" in log_text))
        results.append(check("logs/app.log records tool calls", "tool=" in log_text))
    else:
        results.append(check("logs/app.log exists", False))
        results.append(check("logs/app.log records ci_alert run", False))

    print()
    if all(results):
        print("Step 9 complete.")
        print("Duplicate CI alerts are skipped using logs/state.json.")
        print("View logs: tail -f logs/app.log")
        return 0

    print("Step 9 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
