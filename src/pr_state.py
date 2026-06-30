"""Track which pull requests have already been notified."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PR_NOTIFY_STATE_PATH = ROOT / "logs" / "pr_notify_state.json"


@dataclass
class PrNotifyState:
    notified_pull_numbers: set[int] = field(default_factory=set)
    last_checked_at: str | None = None

    def mark_notified(self, pull_number: int) -> None:
        self.notified_pull_numbers.add(pull_number)
        self.last_checked_at = datetime.now(timezone.utc).isoformat()

    def unseen_pull_numbers(self, open_pull_numbers: list[int]) -> list[int]:
        return [number for number in open_pull_numbers if number not in self.notified_pull_numbers]


def load_pr_notify_state(path: Path | None = None) -> PrNotifyState:
    state_path = path or PR_NOTIFY_STATE_PATH
    if not state_path.exists():
        return PrNotifyState()

    data = json.loads(state_path.read_text(encoding="utf-8"))
    numbers = {int(number) for number in data.get("notified_pull_numbers", [])}
    return PrNotifyState(
        notified_pull_numbers=numbers,
        last_checked_at=data.get("last_checked_at"),
    )


def save_pr_notify_state(state: PrNotifyState, path: Path | None = None) -> Path:
    state_path = path or PR_NOTIFY_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "notified_pull_numbers": sorted(state.notified_pull_numbers),
        "last_checked_at": state.last_checked_at,
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return state_path
