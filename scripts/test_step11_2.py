#!/usr/bin/env python3
"""Step 11.2 — verify Firebase Firestore client."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f": {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def main() -> int:
    print("Step 11.2 — Firebase Firestore Test")
    print(f"Project root: {ROOT}\n")

    results: list[bool] = []
    python = ROOT / "venv" / "bin" / "python"
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    results.append(check("firebase-admin in requirements.txt", "firebase-admin" in requirements))
    results.append(check("src/firebase_store.py exists", (ROOT / "src" / "firebase_store.py").is_file()))
    results.append(check("FIREBASE_PROJECT_ID in .env.example", "FIREBASE_PROJECT_ID" in env_example))
    results.append(
        check(
            "firebase-service-account.json gitignored",
            "config/firebase-service-account.json" in gitignore,
        )
    )

    help_run = subprocess.run(
        [str(python), str(ROOT / "src" / "main.py"), "firebase-test", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    results.append(check("firebase-test command registered", help_run.returncode == 0))

    try:
        from dataclasses import replace

        from config import load_settings
        from firebase_store import FirebaseStoreError, get_session_messages, save_message

        settings = load_settings()
        results.append(
            check(
                "settings.firebase_credentials_path resolved",
                str(settings.firebase_credentials_path).endswith("firebase-service-account.json"),
            )
        )

        try:
            from firebase_store import _require_firebase_config

            _require_firebase_config(replace(settings, firebase_project_id=None))
            results.append(check("missing project id raises FirebaseStoreError", False))
        except FirebaseStoreError:
            results.append(check("missing project id raises FirebaseStoreError", True))

        mock_db = MagicMock()
        mock_session_ref = MagicMock()
        mock_message_ref = MagicMock()
        mock_message_ref.id = "msg-123"
        mock_session_ref.collection.return_value.document.return_value = mock_message_ref
        mock_session_ref.get.return_value.exists = False
        mock_db.collection.return_value.document.return_value = mock_session_ref

        fake_settings = replace(
            settings,
            firebase_project_id="test-project",
            firebase_credentials_path=ROOT / "config" / "firebase-service-account.json",
        )

        with (
            patch("firebase_store.firebase_admin._apps", {}),
            patch("firebase_store.credentials.Certificate"),
            patch("firebase_store.firebase_admin.initialize_app"),
            patch("firebase_store.init_firebase", return_value=mock_db),
        ):
            message_id = save_message(fake_settings, "session-1", "user", "hello", title="Test")
            results.append(check("save_message returns id", message_id == "msg-123"))

            mock_query = MagicMock()
            mock_doc = MagicMock()
            mock_doc.id = "msg-123"
            mock_doc.to_dict.return_value = {
                "role": "user",
                "content": "hello",
                "created_at": "now",
            }
            mock_query.stream.return_value = [mock_doc]
            mock_session_ref.collection.return_value.order_by.return_value.limit.return_value = (
                mock_query
            )

            messages = get_session_messages(fake_settings, "session-1", limit=5)
            results.append(check("get_session_messages returns docs", len(messages) == 1))
    except Exception as error:
        results.append(check("firebase_store unit tests", False, str(error)))

    passed = all(results)
    print(f"\n{'All checks passed.' if passed else 'Some checks failed.'}")
    if passed:
        print("\nNext: set up Firebase and add to .env:")
        print("  FIREBASE_PROJECT_ID=your-project-id")
        print("  Save service account JSON to config/firebase-service-account.json")
        print("Then run: python src/main.py firebase-test")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
