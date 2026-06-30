#!/usr/bin/env python3
"""Step 6 — verify CI alert workflow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 6 — CI Alert Workflow Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/workflows/ci_alert.py exists", (ROOT / "src/workflows/ci_alert.py").is_file()))

    dry_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ci-alert", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = dry_run.stdout + dry_run.stderr
    results.append(check("ci-alert --dry-run runs", dry_run.returncode == 0, output.strip()[:120]))
    results.append(
        check(
            "handles no failures or shows alert",
            "No CI failures" in output or "Dry run: would send CI alert" in output,
        )
    )

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ci-alert", "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    results.append(check("ci-alert --help works", help_run.returncode == 0))
    results.append(check("--dry-run flag documented", "--dry-run" in help_run.stdout))

    print()
    if all(results):
        print("Step 6 tool checks complete.")
        print("Run manually to send a live alert when CI fails: python src/main.py ci-alert")
        return 0

    print("Step 6 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
