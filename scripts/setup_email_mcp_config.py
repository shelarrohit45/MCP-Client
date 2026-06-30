#!/usr/bin/env python3
"""Create ~/.config/email-mcp/config.toml from project settings."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import ConfigError, load_settings
from email_mcp_config import EMAIL_MCP_CONFIG, ensure_email_mcp_config


def main() -> int:
    try:
        settings = load_settings()
        path = ensure_email_mcp_config(settings)
    except ConfigError as error:
        print(f"Configuration error: {error}")
        return 1

    print(f"Email MCP config ready: {path}")
    print("Sender:", settings.email_sender)
    print("Receiver (used by app):", settings.email_receiver)
    if path == EMAIL_MCP_CONFIG and EMAIL_MCP_CONFIG.exists():
        print("Tip: use a Gmail app password in .env if SMTP auth fails.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
