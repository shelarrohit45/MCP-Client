#!/usr/bin/env python3
"""Step 11 — verify OpenRouter agent layer, Firebase memory, and docs."""

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
    print("Step 11 — OpenRouter Agent + Firebase Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    config_yaml = (ROOT / "config" / "config.yaml").read_text(encoding="utf-8")
    config_example = (ROOT / "config" / "config.example.yaml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    agent_modules = [
        "src/llm_client.py",
        "src/firebase_store.py",
        "src/agent_chat.py",
        "src/agent_tools.py",
        "src/agent_loop.py",
        "src/agent_guardrails.py",
        "src/agent_history.py",
    ]
    for module in agent_modules:
        results.append(check(f"{module} exists", (ROOT / module).is_file()))

    results.append(check("httpx in requirements.txt", "httpx" in requirements))
    results.append(check("firebase-admin in requirements.txt", "firebase-admin" in requirements))

    for var in [
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_CREDENTIALS_PATH",
    ]:
        results.append(check(f"{var} in .env.example", var in env_example))

    for key in ["agent:", "max_tool_iterations", "require_confirmation"]:
        results.append(check(f"agent section in config.yaml ({key})", key in config_yaml))
        results.append(check(f"agent section in config.example.yaml ({key})", key in config_example))

    readme_sections = [
        "OpenRouter setup",
        "Firebase setup",
        "llm-test",
        "firebase-test",
        "agent-history",
        "agent-tools",
        "50 requests per day",
        "scheduler does **not** require OpenRouter",
    ]
    for section in readme_sections:
        results.append(check(f"README documents {section}", section in readme))

    agent_commands = ["llm-test", "firebase-test", "ask", "agent-tools", "agent-history"]
    for command in agent_commands:
        help_run = subprocess.run(
            [str(python), str(ROOT / "src" / "main.py"), command, "--help"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        results.append(check(f"{command} --help works", help_run.returncode == 0))

    try:
        from config import load_settings

        settings = load_settings()
        results.append(check("settings.openrouter_model configured", bool(settings.openrouter_model)))
        results.append(check("settings.agent_max_tool_iterations > 0", settings.agent_max_tool_iterations > 0))
        results.append(
            check(
                "settings.firebase_credentials_path resolved",
                str(settings.firebase_credentials_path).endswith("firebase-service-account.json"),
            )
        )
    except Exception as error:  # noqa: BLE001
        results.append(check("config loads agent settings", False, str(error)))

    subtests = sorted(
        path
        for path in (ROOT / "scripts").glob("test_step11_*.py")
        if path.name != "test_step11.py"
    )
    print()
    for script in subtests:
        print(f"--- {script.name} ---")
        run = subprocess.run([str(python), str(script)], cwd=ROOT)
        results.append(check(script.name, run.returncode == 0))
        print()

    print()
    if all(results):
        print("Step 11 complete.")
        print("Try: python src/main.py llm-test")
        print("     python src/main.py firebase-test")
        print('     python src/main.py ask "How many open PRs?"')
        print("     python src/main.py agent-history")
        return 0

    print("Step 11 not complete. Fix failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
