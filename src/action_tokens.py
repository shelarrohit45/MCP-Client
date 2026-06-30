"""Signed tokens for PR merge/reject action links."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass

DEFAULT_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60


class ActionTokenError(Exception):
    """Raised when an action token is invalid or expired."""


@dataclass(frozen=True)
class ActionTokenPayload:
    pull_number: int
    action: str
    expires_at: int


def _sign(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def create_action_token(
    secret: str,
    pull_number: int,
    action: str,
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
) -> str:
    """Create a URL-safe token authorizing a merge or reject action."""
    if action not in {"merge", "reject"}:
        raise ValueError(f"Unsupported action: {action}")

    expires_at = int(time.time()) + ttl_seconds
    message = f"{pull_number}:{action}:{expires_at}"
    signature = _sign(secret, message)
    raw = f"{message}:{signature}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def verify_action_token(secret: str, token: str, pull_number: int, action: str) -> ActionTokenPayload:
    """Validate token for the requested PR action."""
    padding = "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(token + padding).decode()
    except (ValueError, UnicodeDecodeError) as error:
        raise ActionTokenError("Invalid action token.") from error

    parts = decoded.split(":")
    if len(parts) != 4:
        raise ActionTokenError("Malformed action token.")

    token_pull_number, token_action, expires_raw, signature = parts
    if int(token_pull_number) != pull_number or token_action != action:
        raise ActionTokenError("Token does not match this pull request action.")

    message = f"{token_pull_number}:{token_action}:{expires_raw}"
    expected = _sign(secret, message)
    if not hmac.compare_digest(signature, expected):
        raise ActionTokenError("Token signature mismatch.")

    expires_at = int(expires_raw)
    if time.time() > expires_at:
        raise ActionTokenError("Action link has expired.")

    return ActionTokenPayload(pull_number=pull_number, action=action, expires_at=expires_at)
