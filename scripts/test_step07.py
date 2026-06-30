#!/usr/bin/env python3
"""Step 7 — verify HTML CI alert templates."""

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
    print("Step 7 — HTML Templates Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("jinja2 in requirements.txt", "jinja2" in (ROOT / "requirements.txt").read_text()))
    results.append(check("templates/ci_alert.html exists", (ROOT / "templates/ci_alert.html").is_file()))
    results.append(check("src/template_renderer.py exists", (ROOT / "src/template_renderer.py").is_file()))

    try:
        from template_renderer import render_template

        html = render_template(
            "ci_alert.html",
            repo="owner/repo",
            failure_count=1,
            hours=24,
            failures=[
                {
                    "workflow_name": "CI",
                    "branch": "main",
                    "author": "dev",
                    "updated_at": "2026-06-30T12:00:00Z",
                    "url": "https://github.com/owner/repo/actions/runs/1",
                }
            ],
        )
        results.append(check("template renders HTML", "<html" in html and "View on GitHub" in html))
    except Exception as error:  # noqa: BLE001
        results.append(check("template renders HTML", False, str(error)))

    dry_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "ci-alert", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = dry_run.stdout + dry_run.stderr
    results.append(check("ci-alert --dry-run runs", dry_run.returncode == 0))
    results.append(
        check(
            "dry-run handles zero failures or prints HTML",
            "No CI failures" in output or "CI Failure Alert" in output,
        )
    )

    print()
    if all(results):
        print("Step 7 complete.")
        print("When CI fails, run: python src/main.py ci-alert")
        return 0

    print("Step 7 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
