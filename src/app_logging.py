"""Application logging to logs/app.log."""

from __future__ import annotations

import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_LOG_PATH = ROOT / "logs" / "app.log"

_CONFIGURED = False


def setup_logging() -> None:
    """Configure file logging once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    APP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    file_handler = logging.FileHandler(APP_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger("mcp_client")
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under mcp_client."""
    setup_logging()
    return logging.getLogger(f"mcp_client.{name}")


def log_workflow_start(logger: logging.Logger, workflow: str, **details: object) -> None:
    parts = [f"{key}={value}" for key, value in details.items()]
    suffix = f" ({', '.join(parts)})" if parts else ""
    logger.info("workflow=%s event=start%s", workflow, suffix)


def log_workflow_end(
    logger: logging.Logger,
    workflow: str,
    *,
    success: bool,
    detail: str = "",
) -> None:
    status = "success" if success else "failure"
    if detail:
        logger.info("workflow=%s event=end status=%s detail=%s", workflow, status, detail)
    else:
        logger.info("workflow=%s event=end status=%s", workflow, status)


def log_tool_call(
    logger: logging.Logger,
    server: str,
    tool_name: str,
    *,
    success: bool,
    detail: str = "",
) -> None:
    status = "success" if success else "failure"
    if detail:
        logger.info(
            "server=%s tool=%s status=%s detail=%s",
            server,
            tool_name,
            status,
            detail,
        )
    else:
        logger.info("server=%s tool=%s status=%s", server, tool_name, status)
