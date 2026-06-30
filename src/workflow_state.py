"""Persistent workflow state for duplicate prevention."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_STATE_PATH = ROOT / "logs" / "state.json"


@dataclass
class WorkflowState:
    last_ci_alert_at: str | None = None
    alerted_run_ids: set[str] = field(default_factory=set)

    def was_alerted(self, run_id: str) -> bool:
        return run_id in self.alerted_run_ids

    def mark_alerted(self, run_id: str) -> None:
        self.alerted_run_ids.add(run_id)
        self.last_ci_alert_at = datetime.now(timezone.utc).isoformat()


def load_workflow_state(path: Path | None = None) -> WorkflowState:
    state_path = path or WORKFLOW_STATE_PATH
    if not state_path.exists():
        return WorkflowState()

    data = json.loads(state_path.read_text(encoding="utf-8"))
    return WorkflowState(
        last_ci_alert_at=data.get("last_ci_alert_at"),
        alerted_run_ids=set(data.get("alerted_run_ids", [])),
    )


def save_workflow_state(state: WorkflowState, path: Path | None = None) -> Path:
    state_path = path or WORKFLOW_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_ci_alert_at": state.last_ci_alert_at,
        "alerted_run_ids": sorted(state.alerted_run_ids),
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return state_path
