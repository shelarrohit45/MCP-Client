"""Track PR snapshots and which events were already emailed."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PR_EVENT_STATE_PATH = ROOT / "logs" / "pr_event_state.json"
LEGACY_NOTIFY_STATE_PATH = ROOT / "logs" / "pr_notify_state.json"


@dataclass
class PrSnapshot:
    number: int
    state: str
    merged: bool
    title: str
    author: str
    url: str
    branch: str
    review_ids: set[int] = field(default_factory=set)
    head_sha: str = ""
    ci_state: str = ""

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "state": self.state,
            "merged": self.merged,
            "title": self.title,
            "author": self.author,
            "url": self.url,
            "branch": self.branch,
            "review_ids": sorted(self.review_ids),
            "head_sha": self.head_sha,
            "ci_state": self.ci_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PrSnapshot:
        return cls(
            number=int(data["number"]),
            state=str(data.get("state", "unknown")),
            merged=bool(data.get("merged", False)),
            title=str(data.get("title", "")),
            author=str(data.get("author", "")),
            url=str(data.get("url", "")),
            branch=str(data.get("branch", "")),
            review_ids={int(rid) for rid in data.get("review_ids", [])},
            head_sha=str(data.get("head_sha", "")),
            ci_state=str(data.get("ci_state", "")),
        )


@dataclass
class PrEventState:
    snapshots: dict[int, PrSnapshot] = field(default_factory=dict)
    sent_events: set[str] = field(default_factory=set)
    last_checked_at: str | None = None

    def event_key(self, pull_number: int, event_type: str, suffix: str = "") -> str:
        if suffix:
            return f"{pull_number}:{event_type}:{suffix}"
        return f"{pull_number}:{event_type}"

    def was_sent(self, key: str) -> bool:
        return key in self.sent_events

    def mark_sent(self, key: str) -> None:
        self.sent_events.add(key)
        self.last_checked_at = datetime.now(timezone.utc).isoformat()


def _import_legacy_created_events(state: PrEventState) -> None:
    if not LEGACY_NOTIFY_STATE_PATH.exists():
        return
    data = json.loads(LEGACY_NOTIFY_STATE_PATH.read_text(encoding="utf-8"))
    for number in data.get("notified_pull_numbers", []):
        state.mark_sent(state.event_key(int(number), "created"))


def load_pr_event_state(path: Path | None = None) -> PrEventState:
    state_path = path or PR_EVENT_STATE_PATH
    if not state_path.exists():
        state = PrEventState()
        _import_legacy_created_events(state)
        return state

    data = json.loads(state_path.read_text(encoding="utf-8"))
    snapshots = {
        int(number): PrSnapshot.from_dict(snapshot)
        for number, snapshot in data.get("snapshots", {}).items()
    }
    return PrEventState(
        snapshots=snapshots,
        sent_events=set(data.get("sent_events", [])),
        last_checked_at=data.get("last_checked_at"),
    )


def save_pr_event_state(state: PrEventState, path: Path | None = None) -> Path:
    state_path = path or PR_EVENT_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_checked_at": state.last_checked_at,
        "sent_events": sorted(state.sent_events),
        "snapshots": {str(number): snap.to_dict() for number, snap in state.snapshots.items()},
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return state_path
