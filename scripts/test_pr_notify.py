#!/usr/bin/env python3
"""Smoke test PR notification workflow."""

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
    print("PR notification workflow test\n")
    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    for rel in [
        "src/github_pr.py",
        "src/action_tokens.py",
        "src/action_server.py",
        "src/workflows/pr_notify.py",
    ]:
        results.append(check(f"{rel} exists", (ROOT / rel).is_file()))

    from action_tokens import create_action_token, verify_action_token

    token = create_action_token("test-secret", 42, "merge")
    payload = verify_action_token("test-secret", token, 42, "merge")
    results.append(check("action token roundtrip", payload.pull_number == 42))

    dry_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "pr-notify", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**dict(**__import__("os").environ), "ACTION_SECRET": "test-secret-for-ci"},
    )
    output = dry_run.stdout + dry_run.stderr
    results.append(check("pr-notify --dry-run runs", dry_run.returncode == 0, output.strip()[:120]))

    print()
    if all(results):
        print("PR notification checks passed.")
        print("Next:")
        print("  1. Add ACTION_SECRET to .env")
        print("  2. python src/main.py action-server")
        print("  3. python src/main.py pr-notify")
        return 0

    print("Some checks failed.")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    sys.exit(main())
