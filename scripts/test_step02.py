#!/usr/bin/env python3
"""Step 2 — verify config system."""

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
    print("Step 2 — Config System Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("config/config.yaml exists", (ROOT / "config" / "config.yaml").is_file()))
    results.append(check("src/config.py exists", (ROOT / "src" / "config.py").is_file()))
    results.append(check(".env exists", (ROOT / ".env").is_file()))

    run_main = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py")],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = run_main.stdout.strip()
    results.append(check("main.py runs", run_main.returncode == 0, output or run_main.stderr.strip()))
    results.append(check("prints GitHub repo", "GitHub repo:" in output))
    results.append(check("prints recipient count", "Recipients:" in output))
    results.append(
        check(
            "does not print secrets",
            "GITHUB_PERSONAL_ACCESS_TOKEN" not in output
            and "EMAIL_PASSWORD" not in output
            and "ghp_" not in output
            and "github_pat_" not in output,
        )
    )

    missing_env = subprocess.run(
        [str(python), "-c", "import sys; sys.path.insert(0, 'src'); from config import load_settings; load_settings(env_path='.env.missing')"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    results.append(
        check(
            "missing .env shows clear error",
            "Missing .env file" in (missing_env.stdout + missing_env.stderr),
            (missing_env.stdout + missing_env.stderr).strip() or "no output",
        )
    )

    print()
    if all(results):
        print("Step 2 complete. Ready for Step 3.")
        return 0

    print("Step 2 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
