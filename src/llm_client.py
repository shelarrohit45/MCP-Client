"""OpenRouter LLM client for the agent layer (Step 11.1)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app_logging import get_logger
from config import Settings

logger = get_logger("llm")

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 60.0


class LLMClientError(Exception):
    """Raised when an OpenRouter request fails."""


@dataclass(frozen=True)
class ChatResult:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int


def _api_key(settings: Settings) -> str:
    key = (settings.openrouter_api_key or "").strip()
    if not key:
        raise LLMClientError(
            "Missing OPENROUTER_API_KEY in .env. "
            "Create a key at https://openrouter.ai/keys"
        )
    return key


def _model(settings: Settings, model: str | None) -> str:
    chosen = (model or settings.openrouter_model or DEFAULT_MODEL).strip()
    if not chosen:
        raise LLMClientError("Missing OPENROUTER_MODEL in .env or config.")
    return chosen


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise LLMClientError("OpenRouter returned no choices.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        raise LLMClientError("OpenRouter returned an empty message.")

    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        text = "".join(parts).strip()
    else:
        text = str(content).strip()

    if not text:
        raise LLMClientError("OpenRouter returned an empty response.")
    return text


def chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Send a chat completion request to OpenRouter and return assistant text."""
    return chat_completion(
        settings,
        messages,
        model=model,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    ).content


def chat_completion(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> ChatResult:
    """Send a chat completion request and return text plus token usage."""
    api_key = _api_key(settings)
    chosen_model = _model(settings, model)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/mcp-client",
        "X-OpenRouter-Title": "MCP DevOps Client",
    }
    payload = {
        "model": chosen_model,
        "messages": messages,
    }

    last_error = "OpenRouter rate limit exceeded after retries."

    with httpx.Client(timeout=timeout_seconds) as client:
        for attempt in range(max_retries):
            response = client.post(
                OPENROUTER_CHAT_URL,
                headers=headers,
                json=payload,
            )

            if response.status_code == 429:
                wait_seconds = 2**attempt
                logger.warning(
                    "openrouter_rate_limit model=%s attempt=%s wait_seconds=%s",
                    chosen_model,
                    attempt + 1,
                    wait_seconds,
                )
                if attempt + 1 < max_retries:
                    time.sleep(wait_seconds)
                    continue
                raise LLMClientError(last_error)

            if response.status_code == 401:
                raise LLMClientError(
                    "OpenRouter authentication failed. Check OPENROUTER_API_KEY in .env."
                )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                detail = response.text.strip() or str(error)
                raise LLMClientError(
                    f"OpenRouter request failed ({response.status_code}): {detail}"
                ) from error

            data = response.json()
            content = _extract_content(data)
            usage = data.get("usage") or {}
            resolved_model = str(data.get("model", chosen_model))
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
            logger.info(
                "openrouter_chat model=%s prompt_tokens=%s completion_tokens=%s",
                resolved_model,
                prompt_tokens,
                completion_tokens,
            )
            return ChatResult(
                content=content,
                model=resolved_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

    raise LLMClientError(last_error)
