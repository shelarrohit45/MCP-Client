#!/usr/bin/env python3
"""Step 5 — verify Email MCP connection."""

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
    print("Step 5 — Email MCP Connect Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"

    results.append(check("src/email_client.py exists", (ROOT / "src" / "email_client.py").is_file()))
    results.append(
        check(
            "email-mcp installed",
            (ROOT / "node_modules" / "@codefuturist" / "email-mcp" / "dist" / "main.js").is_file(),
            "run ./scripts/install_email_mcp.sh",
        )
    )
    results.append(check("npx available", subprocess.run(["which", "npx"], capture_output=True).returncode == 0))

    list_tools = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "list-email-tools"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    output = (list_tools.stdout + list_tools.stderr).strip()
    tool_lines = [line for line in list_tools.stdout.splitlines() if line.startswith("- ")]
    results.append(check("list-email-tools runs", list_tools.returncode == 0, list_tools.stdout.splitlines()[0] if list_tools.stdout else output[:120]))
    results.append(check("email tools listed", len(tool_lines) > 0, f"{len(tool_lines)} tools"))
    results.append(check("send_email tool present", any("send_email" in line for line in tool_lines)))

    print()
    if all(results):
        print("Step 5 tool checks complete.")
        print("Run manually to verify delivery: python src/main.py send-test-email")
        return 0

    print("Step 5 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
