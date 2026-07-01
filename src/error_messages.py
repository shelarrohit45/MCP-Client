"""User-facing error messages for common failure modes."""

from __future__ import annotations

from email_client import EmailSendError
from github_fetch import GitHubFetchError
from llm_client import LLMClientError
from mcp_manager import MCPConnectionError


def format_error_for_user(error: Exception) -> str:
    """Turn an exception into a clear CLI message."""
    message = str(error).strip() or error.__class__.__name__
    lower = message.lower()

    if isinstance(error, MCPConnectionError):
        if "timeout" in lower or "timed out" in lower:
            return (
                "MCP server timed out. Ensure GitHub/Email MCP is installed "
                "and responsive, then try again."
            )
        if "npx not found" in lower or "node" in lower:
            return f"MCP runtime missing: {message}"
        return f"MCP connection failed: {message}"

    if isinstance(error, EmailSendError):
        return (
            "Email delivery failed (SMTP/MCP). Check EMAIL_PASSWORD in .env and "
            f"config/email-mcp/config.toml. Details: {message}"
        )

    if isinstance(error, GitHubFetchError):
        if "401" in message or "bad credentials" in lower:
            return (
                "GitHub token is invalid or expired. Update GITHUB_TOKEN in .env "
                "with a PAT that has repo access."
            )
        if "403" in message or "forbidden" in lower:
            return (
                "GitHub token lacks permission for this repo. Use a PAT with repo "
                f"read access. Details: {message}"
            )
        return f"GitHub data fetch failed: {message}"

    if isinstance(error, LLMClientError):
        if "missing openrouter_api_key" in lower or "authentication failed" in lower:
            return (
                "OpenRouter API key missing or invalid. Add OPENROUTER_API_KEY to .env "
                "(create one at https://openrouter.ai/keys)."
            )
        if "rate limit" in lower or "429" in message:
            return (
                "OpenRouter rate limit reached. Wait a minute and retry, or use a paid model. "
                f"Details: {message}"
            )
        return f"OpenRouter LLM error: {message}"

    if "401" in message or "bad credentials" in lower:
        return "Authentication failed. Check GITHUB_TOKEN or email credentials in .env."

    if "smtp" in lower:
        return f"SMTP error while sending email: {message}"

    if "timeout" in lower or "timed out" in lower:
        return f"Request timed out: {message}"

    return message
