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

ROOT = Path(__file__).resolve().parent.parent
LOCAL_GITHUB_MCP_BINARY = ROOT / "bin" / "github-mcp-server"


class MCPConnectionError(Exception):
    """Raised when the GitHub MCP server cannot be started."""


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
async def github_mcp_session(github_token: str) -> AsyncIterator[ClientSession]:
    """Open a connected GitHub MCP session."""
    params = resolve_github_server_params(github_token)
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


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
