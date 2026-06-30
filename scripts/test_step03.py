#!/usr/bin/env python3
"""Step 3 — verify GitHub MCP connection."""

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
    print("Step 3 — GitHub MCP Connect Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"
    binary = ROOT / "bin" / "github-mcp-server"

    results.append(check("src/mcp_manager.py exists", (ROOT / "src" / "mcp_manager.py").is_file()))
    results.append(
        check(
            "GitHub MCP binary available",
            binary.exists(),
            str(binary) if binary.exists() else "Run ./scripts/install_github_mcp.sh",
        )
    )

    run_list = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "list-github-tools"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = (run_list.stdout + run_list.stderr).strip()
    tool_lines = [line for line in run_list.stdout.splitlines() if line.startswith("- ")]
    results.append(check("list-github-tools runs", run_list.returncode == 0, output.splitlines()[0] if output else "no output"))
    results.append(check("tools listed", len(tool_lines) > 0, f"{len(tool_lines)} tools"))
    results.append(check("no auth error", "401" not in output and "Unauthorized" not in output))

    print()
    if all(results):
        print("Step 3 complete. Ready for Step 4.")
        return 0

    print("Step 3 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
