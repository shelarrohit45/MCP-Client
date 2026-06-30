"""Manage Email MCP config.toml for the project."""

from __future__ import annotations

import json
from pathlib import Path

from config import Settings

ROOT = Path(__file__).resolve().parent.parent
EMAIL_MCP_CONFIG_ROOT = ROOT / "config"
EMAIL_MCP_CONFIG_DIR = EMAIL_MCP_CONFIG_ROOT / "email-mcp"
EMAIL_MCP_CONFIG = EMAIL_MCP_CONFIG_DIR / "config.toml"
DEFAULT_EMAIL_ACCOUNT = "default"


def render_config(settings: Settings) -> str:
    use_starttls = settings.email_smtp_port == 587
    smtp_tls = "false" if use_starttls else "true"
    starttls = "true" if use_starttls else "false"

    return f"""[settings]
rate_limit = 10

[[accounts]]
name = "{DEFAULT_EMAIL_ACCOUNT}"
email = "{settings.email_sender}"
full_name = "MCP Client"
password = {json.dumps(settings.email_password)}

[accounts.imap]
host = "{settings.email_imap_host}"
port = {settings.email_imap_port}
tls = true

[accounts.smtp]
host = "{settings.email_smtp_host}"
port = {settings.email_smtp_port}
tls = {smtp_tls}
starttls = {starttls}
verify_ssl = true

[accounts.smtp.pool]
enabled = true
max_connections = 1
max_messages = 100
"""


def ensure_email_mcp_config(settings: Settings) -> Path:
    """Create or refresh project-local Email MCP config from settings."""
    EMAIL_MCP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    EMAIL_MCP_CONFIG.write_text(render_config(settings), encoding="utf-8")
    return EMAIL_MCP_CONFIG


def email_mcp_config_env() -> dict[str, str]:
    """Point Email MCP at the project-local config directory."""
    return {"XDG_CONFIG_HOME": str(EMAIL_MCP_CONFIG_ROOT)}
