#!/usr/bin/env python3
"""Step 0 — verify software and credential files are ready."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else None


def parse_python_version(version_line: str) -> tuple[int, int] | None:
    match = re.search(r"(\d+)\.(\d+)", version_line)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def check_python() -> tuple[bool, str]:
  candidates = [
      ["/opt/homebrew/bin/python3.12"],
      ["python3.12"],
      ["python3"],
  ]

  for command in candidates:
      if not shutil.which(command[0]):
          continue
      version_line = run_version(command + ["--version"])
      if not version_line:
          continue
      parsed = parse_python_version(version_line)
      if parsed and parsed >= (3, 10):
          return True, f"{version_line} ({command[0]})"
      return False, f"{version_line} — need Python 3.10+ (use Homebrew python3.12)"

  return False, "Python 3 not found"


def check_node() -> tuple[bool, str]:
    version_line = run_version(["node", "--version"])
    if not version_line:
        return False, "Node.js not found"

    match = re.search(r"v?(\d+)", version_line)
    major = int(match.group(1)) if match else 0
    if major >= 18:
        return True, version_line
    return False, f"{version_line} — need Node.js 18+"


def check_git() -> tuple[bool, str]:
    version_line = run_version(["git", "--version"])
    if not version_line:
        return False, "Git not found"
    return True, version_line


def check_docker() -> tuple[bool, str]:
    version_line = run_version(["docker", "--version"])
    if not version_line:
        return False, "Not installed (optional — GitHub MCP binary works without Docker)"
    return True, version_line


def _is_placeholder_email(email: str) -> bool:
    return not email or "example.com" in email.lower()


def check_email_config() -> tuple[bool, str]:
    config_path = ROOT / "config" / "config.yaml"
    if not config_path.exists():
        return False, "Missing config/config.yaml"

    contents = config_path.read_text()
    sender_match = re.search(r'^\s*sender:\s*["\']?([^"\']+)["\']?\s*$', contents, re.MULTILINE)
    receiver_match = re.search(r'^\s*receiver:\s*["\']?([^"\']+)["\']?\s*$', contents, re.MULTILINE)

    sender = (sender_match.group(1) if sender_match else "").strip()
    receiver = (receiver_match.group(1) if receiver_match else "").strip()

    if _is_placeholder_email(sender) or _is_placeholder_email(receiver):
        return False, "Set static sender and receiver in config/config.yaml"

    return True, f"{sender} → {receiver}"


def check_env_file() -> tuple[bool, str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return False, "Missing .env — copy .env.example to .env and add your credentials"

    contents = env_path.read_text()
    required = [
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "EMAIL_PASSWORD",
    ]
    missing = []
    for key in required:
        match = re.search(rf"^{key}=(.*)$", contents, re.MULTILINE)
        if not match or not match.group(1).strip():
            missing.append(key)

    if missing:
        return False, f".env missing values: {', '.join(missing)}"
    return True, "GitHub token + sender app password present"


def check_git_remote() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False, "No git remote 'origin' found"

    url = result.stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
    if match:
        return True, f"{match.group(1)}/{match.group(2)}"
    return True, url


def print_result(label: str, ok: bool, detail: str, required: bool = True) -> None:
    tag = "PASS" if ok else ("WARN" if not required else "FAIL")
    suffix = "" if required or ok else " (optional)"
    print(f"[{tag}] {label}{suffix}: {detail}")


def main() -> int:
    print("Step 0 — Prerequisites Check")
    print(f"Project root: {ROOT}\n")

    checks: list[tuple[str, bool, str, bool]] = []

    ok, detail = check_python()
    checks.append(("Python 3.10+", ok, detail, True))

    ok, detail = check_node()
    checks.append(("Node.js 18+", ok, detail, True))

    ok, detail = check_git()
    checks.append(("Git", ok, detail, True))

    ok, detail = check_docker()
    checks.append(("Docker", ok, detail, False))

    ok, detail = check_git_remote()
    checks.append(("GitHub repo", ok, detail, True))

    ok, detail = check_email_config()
    checks.append(("Email sender → receiver", ok, detail, True))

    ok, detail = check_env_file()
    checks.append(("Secrets (.env)", ok, detail, True))

    for label, ok, detail, required in checks:
        print_result(label, ok, detail, required)

    required_failures = [c for c in checks if c[3] and not c[1]]
    optional_failures = [c for c in checks if not c[3] and not c[1]]

    print()
    if required_failures:
        print("Step 0 not complete yet.")
        if any(c[0] in ("Secrets (.env)", "Email sender → receiver") for c in required_failures):
            print("\nNext actions:")
            print("  1. Set sender + receiver in config/config.yaml")
            print("  2. Create GitHub PAT: https://github.com/settings/tokens")
            print("  3. Create app password for SENDER account (Gmail: https://myaccount.google.com/apppasswords)")
            print("  4. Fill GITHUB_PERSONAL_ACCESS_TOKEN and EMAIL_PASSWORD in .env")
        return 1

    if optional_failures:
        print("Step 0 complete for required items. Optional tools missing:")
        for label, _, detail, _ in optional_failures:
            print(f"  - {label}: {detail}")
    else:
        print("Step 0 complete. Ready for Step 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
