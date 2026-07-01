"""Load application settings from config.yaml and .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "config.yaml"
DEFAULT_ENV_PATH = ROOT / ".env"


class ConfigError(Exception):
    """Raised when configuration files or required values are missing."""


@dataclass(frozen=True)
class Settings:
    github_owner: str
    github_repo: str
    email_sender: str
    email_receiver: str
    email_recipients: list[str]
    github_token: str
    email_password: str
    email_smtp_host: str
    email_smtp_port: int
    email_imap_host: str
    email_imap_port: int
    digest_time: str
    ci_check_interval_minutes: int
    action_base_url: str
    action_port: int
    action_secret: str
    pr_check_interval_minutes: int
    openrouter_api_key: str | None
    openrouter_model: str

    @property
    def github_repo_full(self) -> str:
        return f"{self.github_owner}/{self.github_repo}"


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _email_recipients(email_cfg: dict) -> list[str]:
    recipients = email_cfg.get("recipients") or []
    if recipients:
        return [str(email).strip() for email in recipients if str(email).strip()]

    receiver = str(email_cfg.get("receiver", "")).strip()
    if receiver:
        return [receiver]

    return []


def load_settings(
    config_path: Path | str | None = None,
    env_path: Path | str | None = None,
) -> Settings:
    """Load settings from YAML config and environment variables."""
    config_file = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    env_file = Path(env_path) if env_path else DEFAULT_ENV_PATH

    if not config_file.exists():
        raise ConfigError(
            f"Missing config file: {config_file}. "
            "Copy config/config.example.yaml to config/config.yaml."
        )

    if not env_file.exists():
        raise ConfigError(
            f"Missing .env file: {env_file}. Copy .env.example to .env and fill in secrets."
        )

    load_dotenv(env_file)

    with config_file.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    github_cfg = data.get("github", {})
    email_cfg = data.get("email", {})
    schedule_cfg = data.get("schedule", {})
    pr_cfg = data.get("pr_notify", {})
    agent_cfg = data.get("agent", {})

    github_owner = str(github_cfg.get("owner", "")).strip() or _require_env("GITHUB_OWNER")
    github_repo = str(github_cfg.get("repo", "")).strip() or _require_env("GITHUB_REPO")
    email_sender = str(email_cfg.get("sender", "")).strip()
    email_receiver = str(email_cfg.get("receiver", "")).strip()
    recipients = _email_recipients(email_cfg)

    if not email_sender:
        raise ConfigError("Missing email.sender in config/config.yaml")
    if not recipients:
        raise ConfigError("Missing email.receiver or email.recipients in config/config.yaml")

    return Settings(
        github_owner=github_owner,
        github_repo=github_repo,
        email_sender=email_sender,
        email_receiver=email_receiver or recipients[0],
        email_recipients=recipients,
        github_token=_require_env("GITHUB_PERSONAL_ACCESS_TOKEN"),
        email_password=_require_env("EMAIL_PASSWORD"),
        email_smtp_host=os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com").strip(),
        email_smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
        email_imap_host=os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com").strip(),
        email_imap_port=int(os.getenv("EMAIL_IMAP_PORT", "993")),
        digest_time=str(schedule_cfg.get("digest_time", "09:00")),
        ci_check_interval_minutes=int(schedule_cfg.get("ci_check_interval_minutes", 30)),
        action_base_url=os.getenv("ACTION_BASE_URL", str(pr_cfg.get("action_base_url", "http://127.0.0.1:8765"))).strip().rstrip("/"),
        action_port=int(os.getenv("ACTION_PORT", str(pr_cfg.get("action_port", 8765)))),
        action_secret=os.getenv("ACTION_SECRET", str(pr_cfg.get("action_secret", ""))).strip()
        or _require_env("ACTION_SECRET"),
        pr_check_interval_minutes=int(
            os.getenv("PR_CHECK_INTERVAL_MINUTES", str(pr_cfg.get("check_interval_minutes", 5)))
        ),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip() or None,
        openrouter_model=(
            os.getenv("OPENROUTER_MODEL", str(agent_cfg.get("model", "openrouter/free"))).strip()
            or "openrouter/free"
        ),
    )
