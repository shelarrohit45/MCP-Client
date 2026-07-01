#!/usr/bin/env python3
"""Step 11.1 — verify OpenRouter LLM client."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 11.1 — OpenRouter LLM Client Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    results.append(check("httpx in requirements.txt", "httpx" in requirements))
    results.append(check("src/llm_client.py exists", (ROOT / "src" / "llm_client.py").is_file()))
    results.append(check("OPENROUTER_API_KEY in .env.example", "OPENROUTER_API_KEY" in env_example))
    results.append(check("OPENROUTER_MODEL in .env.example", "OPENROUTER_MODEL" in env_example))

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "llm-test", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("llm-test command registered", help_run.returncode == 0))

    try:
        from config import load_settings
        from llm_client import LLMClientError, _extract_content, chat

        settings = load_settings()
        results.append(check("settings.openrouter_model loaded", bool(settings.openrouter_model)))

        content = _extract_content(
            {"choices": [{"message": {"content": "hello"}}]}
        )
        results.append(check("_extract_content parses string", content == "hello"))

        with patch("llm_client.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "model": "openrouter/free",
                "choices": [{"message": {"content": "MCP client LLM test OK"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_response.raise_for_status.return_value = None
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response

            fake_settings = settings
            object.__setattr__(fake_settings, "openrouter_api_key", "sk-or-test-key")

            result = chat(fake_settings, [{"role": "user", "content": "test"}])
            results.append(check("chat() returns assistant text", result == "MCP client LLM test OK"))

        try:
            object.__setattr__(settings, "openrouter_api_key", None)
            chat(settings, [{"role": "user", "content": "test"}])
            results.append(check("missing API key raises LLMClientError", False))
        except LLMClientError:
            results.append(check("missing API key raises LLMClientError", True))
    except Exception as error:
        results.append(check("llm_client unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nNext: add OPENROUTER_API_KEY to .env, then run:")
        print("  python src/main.py llm-test")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
