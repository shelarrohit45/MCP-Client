#!/usr/bin/env python3
"""Step 10 — verify scheduler and project README."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 10 — Scheduler + Docs Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    results.append(check("apscheduler in requirements.txt", "apscheduler" in requirements))
    results.append(check("src/scheduler.py exists", (ROOT / "src" / "scheduler.py").is_file()))
    results.append(check("README.md exists", (ROOT / "README.md").is_file()))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for section in [
        "Prerequisites",
        "CLI commands",
        "run-scheduler",
        "Troubleshooting",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
    ]:
        results.append(check(f"README mentions {section}", section in readme))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "run-scheduler", "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    results.append(check("run-scheduler --help works", help_run.returncode == 0))

    try:
        from config import load_settings
        from scheduler import build_scheduler, parse_digest_time

        hour, minute = parse_digest_time("09:00")
        results.append(check("parse_digest_time works", hour == 9 and minute == 0))

        settings = load_settings()
        scheduler = build_scheduler(settings)
        job_ids = {job.id for job in scheduler.get_jobs()}
        results.append(check("scheduler registers ci_alert job", "ci_alert" in job_ids))
        results.append(check("scheduler registers daily_digest job", "daily_digest" in job_ids))
    except Exception as error:  # noqa: BLE001
        results.append(check("scheduler unit tests", False, str(error)))

    print()
    if all(results):
        print("Step 10 complete.")
        print("Start automation: python src/main.py run-scheduler")
        print("Project README: README.md")
        return 0

    print("Step 10 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
