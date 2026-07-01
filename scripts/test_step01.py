#!/usr/bin/env python3
"""Step 1 — verify basic project setup."""

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
    print("Step 1 — Basic Project Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []

    for folder in ("src", "templates", "logs", "tests", "config"):
        results.append(check(f"Folder {folder}/", (ROOT / folder).is_dir()))

    for file in ("src/main.py", "requirements.txt", ".gitignore"):
        results.append(check(f"File {file}", (ROOT / file).is_file()))

    gitignore = (ROOT / ".gitignore").read_text()
    results.append(check("venv/ in .gitignore", "venv/" in gitignore))

    python = ROOT / "venv" / "bin" / "python"
    if not python.exists():
        results.append(check("venv/bin/python exists", False))
    else:
        version = subprocess.run(
            [str(python), "--version"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        major_minor = tuple(int(x) for x in version.split()[1].split(".")[:2])
        results.append(check("Python 3.10+", major_minor >= (3, 10), version))

        run_main = subprocess.run(
            [str(python), str(ROOT / "src" / "main.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        output = run_main.stdout.strip()
        first_line = output.splitlines()[0] if output else ""
        results.append(
            check(
                "main.py output",
                run_main.returncode == 0 and first_line == "MCP client started",
                first_line or run_main.stderr.strip(),
            )
        )

        imports = subprocess.run(
            [str(python), "-c", "import mcp, dotenv, yaml"],
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(
            check(
                "Package imports (mcp, dotenv, yaml)",
                imports.returncode == 0,
                imports.stderr.strip() or "OK",
            )
        )

    print()
    if all(results):
        print("Step 1 complete. Ready for Step 2.")
        return 0

    print("Step 1 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
