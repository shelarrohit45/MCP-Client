"""Send emails via the Email MCP server."""

from __future__ import annotations

from config import Settings
from email_mcp_config import DEFAULT_EMAIL_ACCOUNT
from mcp_manager import call_email_tool_sync, extract_text_result


class EmailSendError(Exception):
    """Raised when sending email through MCP fails."""


def send_email(
    settings: Settings,
    *,
    subject: str,
    body: str,
    html: bool = False,
) -> str:
    """Send an email to configured recipients."""
    result = call_email_tool_sync(
        settings,
        "send_email",
        {
            "account": DEFAULT_EMAIL_ACCOUNT,
            "to": settings.email_recipients,
            "subject": subject,
            "body": body,
            "html": html,
        },
    )

    if result.isError:
        raise EmailSendError(extract_text_result(result).strip() or "send_email failed")

    return extract_text_result(result).strip() or "Email sent."


def send_test_email(settings: Settings) -> str:
    """Send a plain-text test email from sender to receiver."""
    return send_email(
        settings,
        subject="MCP Test",
        body="Hello from MCP client",
        html=False,
    )
