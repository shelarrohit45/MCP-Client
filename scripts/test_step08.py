#!/usr/bin/env python3
"""Step 8 — verify daily digest workflow."""

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
    print("Step 8 — Daily Digest Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/workflows/daily_digest.py exists", (ROOT / "src/workflows/daily_digest.py").is_file()))
    results.append(check("templates/digest.html exists", (ROOT / "templates/digest.html").is_file()))

    try:
        from template_renderer import render_template

        html = render_template(
            "digest.html",
            repo="owner/repo",
            date="2026-06-30",
            hours=24,
            open_pr_count=1,
            open_prs=[
                {
                    "number": 1,
                    "title": "Test PR",
                    "author": "dev",
                    "url": "https://github.com/owner/repo/pull/1",
                }
            ],
            open_issue_count=2,
            failed_ci_count=0,
            failed_ci=[],
            successful_ci_count=1,
            successful_ci=[],
            latest_release=None,
            errors=[],
        )
        results.append(check("digest template renders", "<html" in html and "Daily Digest" in html))
        results.append(check("empty sections render", "No CI failures" in html and "No releases" in html))
    except Exception as error:  # noqa: BLE001
        results.append(check("digest template renders", False, str(error)))

    try:
        from workflows.daily_digest import build_digest_subject
        from config import load_settings

        settings = load_settings()
        subject = build_digest_subject(settings, "2026-06-30")
        results.append(
            check(
                "subject line format",
                subject.startswith("[Daily Digest]") and settings.github_repo_full in subject,
                subject,
            )
        )
    except Exception as error:  # noqa: BLE001
        results.append(check("subject line format", False, str(error)))

    dry_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "digest", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = dry_run.stdout + dry_run.stderr
    results.append(check("digest --dry-run runs", dry_run.returncode == 0))
    results.append(
        check(
            "dry-run shows digest preview",
            "Daily Digest" in output and "Dry run" in output,
        )
    )

    print()
    if all(results):
        print("Step 8 complete.")
        print("Preview: python src/main.py digest --dry-run")
        print("Send:    python src/main.py digest --send")
        return 0

    print("Step 8 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
