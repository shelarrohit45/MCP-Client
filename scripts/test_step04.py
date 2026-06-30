#!/usr/bin/env python3
"""Step 4 — verify GitHub data fetch."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT / "logs" / "github_sample.json"


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 4 — GitHub Data Fetch Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/github_fetch.py exists", (ROOT / "src" / "github_fetch.py").is_file()))

    run_fetch = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "fetch-github"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = (run_fetch.stdout + run_fetch.stderr).strip()
    results.append(check("fetch-github runs", run_fetch.returncode == 0, run_fetch.stdout.splitlines()[0] if run_fetch.stdout else output[:120]))
    results.append(check("prints open PR count", "Open PRs:" in run_fetch.stdout))
    results.append(check("prints failed CI count", "Failed CI (last 24h):" in run_fetch.stdout))
    results.append(check("sample JSON saved", SAMPLE_PATH.is_file(), str(SAMPLE_PATH)))

    if SAMPLE_PATH.is_file():
        data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        results.append(check("JSON has repo field", "repo" in data))
        results.append(check("JSON has raw field", "raw" in data))
        results.append(check("JSON has open_pull_requests", "open_pull_requests" in data))
        results.append(check("JSON has failed_runs", "failed_runs" in data))

    print()
    if all(results):
        print("Step 4 complete. Ready for Step 5.")
        return 0

    print("Step 4 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
