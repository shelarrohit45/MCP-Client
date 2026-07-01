# Firebase Firestore — Agent Memory

The agent layer uses **Firebase Firestore** (not Realtime Database) for durable chat memory and audit history.

## Why Firestore?

| Requirement | Firestore fit |
|-------------|----------------|
| Persist chat across CLI restarts | Document store with subcollections |
| Query recent sessions/runs | Indexed collections with `order_by` |
| Audit trail for tool calls | Append-only `workflow_history` |
| No local SQLite ops | Managed cloud DB, service account auth |
| Industry practice for agent apps | Common pattern for session + run logging |

Local `logs/app.log` remains for debugging; Firestore is the **durable audit trail**.

## Project setup

1. Create a project at [Firebase Console](https://console.firebase.google.com).
2. **Build → Firestore Database → Create database** (choose a region).
3. **Project settings → Service accounts → Generate new private key**.
4. Save JSON as `config/firebase-service-account.json` (gitignored).
5. Add to `.env`:
   ```env
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
   ```

## Collections schema

### `agent_sessions/{sessionId}`

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | First user message (truncated) |
| `created_at` | timestamp | Session created |
| `updated_at` | timestamp | Last activity |

### `agent_sessions/{sessionId}/messages/{messageId}`

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | `user`, `assistant`, or `tool` |
| `content` | string | Message text |
| `tool_name` | string? | Set for tool execution records |
| `tool_result` | map? | Optional structured result |
| `created_at` | timestamp | When saved |

### `agent_runs/{runId}`

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string? | Linked chat session |
| `model` | string | OpenRouter model used |
| `prompt_tokens` | int | Input tokens |
| `completion_tokens` | int | Output tokens |
| `tools_called` | array | Tool names invoked |
| `llm_calls` | int | LLM round-trips in loop |
| `latency_ms` | float | Total LLM latency |
| `success` | bool | Run succeeded |
| `error` | string? | Error message if failed |
| `created_at` | timestamp | When logged |

### `workflow_history/{entryId}`

| Field | Type | Description |
|-------|------|-------------|
| `workflow` | string | e.g. `fetch_github_summary`, `agent_confirmation` |
| `status` | string | e.g. `success`, `denied`, `approved` |
| `summary` | string | Human-readable description |
| `metadata` | map | `session_id`, `tool`, etc. |
| `created_at` | timestamp | When logged |

## Implementation (`src/firebase_store.py`)

- **Singleton init**: `firebase_admin` initialized once per process via service account.
- **Write paths**: `save_message`, `log_agent_run`, `log_workflow_history`.
- **Read paths**: `get_session_messages`, `list_recent_sessions`, `list_recent_agent_runs`, `list_recent_workflow_history`.
- **Connectivity test**: `run_firebase_connectivity_test()` — write/read round-trip for `firebase-test` CLI.

## How to test Firebase

### 1. CLI connectivity test

```bash
cd mcp-client
source venv/bin/activate
python src/main.py firebase-test
```

**Pass if:** prints `project_id`, `session_id`, `message_id`, `run_id` with no errors.

### 2. Agent writes data

```bash
python src/main.py ask --dry-run "How many open PRs do I have?"
```

Note the `Session: session-...` in output.

### 3. View history from CLI

```bash
python src/main.py agent-history
python src/main.py agent-history --session session-abc123
```

### 4. View in Firebase Console

1. Open [Firebase Console](https://console.firebase.google.com) → your project.
2. **Build → Firestore Database → Data**.
3. Browse:
   - `agent_sessions` → pick a session → `messages` subcollection
   - `agent_runs`
   - `workflow_history`

### 5. Automated test (no live Firebase)

```bash
python scripts/test_step11_2.py
python scripts/test_step11_7.py
```

Uses mocks — validates code paths without cloud credentials.

## Security (production)

| Rule | Action |
|------|--------|
| Never commit service account JSON | Listed in `.gitignore` |
| Lock Firestore rules | Replace test-mode rules before shared use |
| Least privilege | Service account only needs Firestore access |
| Secrets in `.env` only | `FIREBASE_PROJECT_ID`, path to JSON |

Example restrictive rule (adjust for your app):

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;  // Client SDK blocked; server uses Admin SDK
    }
  }
}
```

The Python app uses the **Firebase Admin SDK** with a service account — it bypasses client security rules. Rules matter if you add a web/mobile client later.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Missing FIREBASE_PROJECT_ID` | Set in `.env` |
| `credentials file not found` | Download service account JSON to `config/` |
| HTTP 404 / database not found | Create Firestore database in console |
| Permission denied | Regenerate key; check project id matches |
| Empty `agent-history` | Run `ask` or `firebase-test` first to create data |
