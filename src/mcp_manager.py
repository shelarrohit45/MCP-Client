"""Connect to MCP servers and invoke tools."""

from __future__ import annotations

import os
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent

from config import Settings
from email_mcp_config import email_mcp_config_env, ensure_email_mcp_config

ROOT = Path(__file__).resolve().parent.parent
LOCAL_GITHUB_MCP_BINARY = ROOT / "bin" / "github-mcp-server"
LOCAL_EMAIL_MCP_BINARY = ROOT / "node_modules" / ".bin" / "email-mcp"
LOCAL_EMAIL_MCP_ENTRY = ROOT / "node_modules" / "@codefuturist" / "email-mcp" / "dist" / "main.js"


def _is_email_mcp_shutdown_error(error: BaseException) -> bool:
    if error.__class__.__name__ == "BrokenResourceError":
        return True
    if isinstance(error, BaseExceptionGroup) and len(error.exceptions) == 1:
        return _is_email_mcp_shutdown_error(error.exceptions[0])
    return False


class MCPConnectionError(Exception):
    """Raised when an MCP server cannot be started or contacted."""


def build_email_mcp_env(settings: Settings) -> dict[str, str]:
    """Build environment for the Email MCP server subprocess."""
    env = os.environ.copy()
    env.update(email_mcp_config_env())
    return env


def resolve_email_server_params(settings: Settings) -> StdioServerParameters:
    """Launch Email MCP via npx using host config or env credentials."""
    npx = shutil.which("npx")
    if not npx:
        raise MCPConnectionError(
            "npx not found. Install Node.js 18+ to use the Email MCP server."
        )

    if not settings.email_password:
        raise MCPConnectionError("EMAIL_PASSWORD is empty in .env")

    ensure_email_mcp_config(settings)

    node = shutil.which("node")
    if node and LOCAL_EMAIL_MCP_ENTRY.exists():
        command = node
        args = [str(LOCAL_EMAIL_MCP_ENTRY), "stdio"]
    elif LOCAL_EMAIL_MCP_BINARY.exists():
        command = str(LOCAL_EMAIL_MCP_BINARY)
        args = ["stdio"]
    elif shutil.which("email-mcp"):
        command = "email-mcp"
        args = ["stdio"]
    else:
        command = npx
        args = ["-y", "@codefuturist/email-mcp", "stdio"]

    return StdioServerParameters(
        command=command,
        args=args,
        env=build_email_mcp_env(settings),
        cwd=str(ROOT),
    )


def resolve_github_server_params(github_token: str) -> StdioServerParameters:
    """Pick the best available way to launch the GitHub MCP server."""
    env = os.environ.copy()
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

    custom_path = os.getenv("GITHUB_MCP_SERVER_PATH", "").strip()
    if custom_path:
        return StdioServerParameters(command=custom_path, args=["stdio"], env=env)

    if LOCAL_GITHUB_MCP_BINARY.exists():
        return StdioServerParameters(
            command=str(LOCAL_GITHUB_MCP_BINARY),
            args=["stdio"],
            env=env,
        )

    if shutil.which("github-mcp-server"):
        return StdioServerParameters(command="github-mcp-server", args=["stdio"], env=env)

    if shutil.which("docker"):
        return StdioServerParameters(
            command="docker",
            args=[
                "run",
                "-i",
                "--rm",
                "-e",
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/github/github-mcp-server",
            ],
            env=env,
        )

    raise MCPConnectionError(
        "GitHub MCP server not found. Install it with:\n"
        "  ./scripts/install_github_mcp.sh\n"
        "Or set GITHUB_MCP_SERVER_PATH to the binary path.\n"
        "Or install Docker and use the official container image."
    )


@asynccontextmanager
async def email_mcp_session(settings: Settings) -> AsyncIterator[ClientSession]:
    """Open a connected Email MCP session."""
    params = resolve_email_server_params(settings)
    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session
    except BaseExceptionGroup as group:
        if not _is_email_mcp_shutdown_error(group):
            raise


@asynccontextmanager
async def github_mcp_session(github_token: str) -> AsyncIterator[ClientSession]:
    """Open a connected GitHub MCP session."""
    params = resolve_github_server_params(github_token)
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def list_email_tools(settings: Settings) -> list[str]:
    """Return tool names exposed by the Email MCP server."""
    async with email_mcp_session(settings) as session:
        result = await session.list_tools()
        return [tool.name for tool in result.tools]


async def call_email_tool(
    settings: Settings,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> CallToolResult:
    """Call an Email MCP tool by name."""
    async with email_mcp_session(settings) as session:
        return await session.call_tool(tool_name, arguments or {})


async def list_github_tools(github_token: str) -> list[str]:
    """Return tool names exposed by the GitHub MCP server."""
    async with github_mcp_session(github_token) as session:
        result = await session.list_tools()
        return [tool.name for tool in result.tools]


async def call_github_tool(
    github_token: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> CallToolResult:
    """Call a GitHub MCP tool by name."""
    async with github_mcp_session(github_token) as session:
        return await session.call_tool(tool_name, arguments or {})


def _run_async(async_fn, /, *args):
    try:
        return anyio.run(async_fn, *args)
    except* Exception as group:
        if len(group.exceptions) == 1:
            error = group.exceptions[0]
            if error.__class__.__name__ == "BrokenResourceError":
                raise MCPConnectionError(
                    "Email MCP server exited unexpectedly. "
                    "Check config/email-mcp/config.toml and use a Gmail app password in .env."
                ) from error
            raise error from group
        raise MCPConnectionError(
            "Email MCP connection failed. "
            "Run: python scripts/setup_email_mcp_config.py\n"
            f"Details: {group.exceptions[0]}"
        ) from group


def list_email_tools_sync(settings: Settings) -> list[str]:
    """Synchronous wrapper for list_email_tools."""
    return _run_async(list_email_tools, settings)


def call_email_tool_sync(
    settings: Settings,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> CallToolResult:
    """Synchronous wrapper for call_email_tool."""
    return _run_async(call_email_tool, settings, tool_name, arguments)


def list_github_tools_sync(github_token: str) -> list[str]:
    """Synchronous wrapper for list_github_tools."""
    return anyio.run(list_github_tools, github_token)


def call_github_tool_sync(
    github_token: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> CallToolResult:
    """Synchronous wrapper for call_github_tool."""
    return anyio.run(call_github_tool, github_token, tool_name, arguments)


def extract_text_result(result: CallToolResult) -> str:
    """Join text content blocks from a tool result."""
    chunks: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent):
            chunks.append(block.text)
    return "\n".join(chunks)
