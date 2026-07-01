# Step 11 — OpenRouter Agent + Firebase Memory

**Goal:** Add an industry-standard LLM agent layer on top of the existing MCP workflows, using **OpenRouter** for the model and **Firebase Firestore** for persistent memory and history.

**Estimated time:** 2–3 weeks (one sub-step at a time)

**Prerequisite:** Step 10 complete (scheduler + README working).

---

## Why this step

Steps 0–10 built a **deterministic automation client** (CLI → workflows → MCP tools).

Step 11 adds what is missing for an industry-standard agent:

| Missing today | Added in Step 11 |
|---------------|------------------|
| No LLM / reasoning | OpenRouter API |
| No natural language | `ask` / `chat` CLI |
| No agent loop | Think → tool call → observe → respond |
| File-only state (`logs/*.json`) | **Firebase Firestore** for history |
| No dynamic tool selection | LLM picks from your existing workflows |

**Important:** Keep the existing scheduler and workflows. The LLM orchestrates them — it does not replace every scheduled poll (free tier limits ~50 requests/day).

---

## Prerequisites

### 1. OpenRouter

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Create an API key: **Settings → Keys** (`sk-or-v1-...`)
3. For development, use a free model:
   - `openrouter/free` — auto-picks a free model with tool support
   - Or `meta-llama/llama-3.3-70b-instruct:free`

Docs: [Quickstart](https://openrouter.ai/docs/quickstart) · [Free models](https://openrouter.ai/docs/guides/routing/model-variants/free) · [Tool calling](https://openrouter.ai/docs/guides/features/tool-calling)

### 2. Firebase (Firestore — not SQLite)

1. Create a project at [Firebase Console](https://console.firebase.google.com)
2. Enable **Firestore Database** (start in **test mode** for dev, lock down rules before production)
3. Create a **service account** key:
   - Project Settings → Service accounts → Generate new private key
4. Save the JSON file as `config/firebase-service-account.json` (gitignored)
5. Note your **Project ID**

**Why Firebase instead of SQLite?**
- Cloud-backed — history survives machine restarts and works across devices
- Real-time sync if you add a web UI later
- Scales without managing local DB files
- Industry-standard for agent session + run logging

---

## Architecture

```
User (natural language)
        ↓
   src/agent_loop.py      ← OpenRouter LLM + tool-calling loop
        ↓
   src/agent_tools.py     ← wraps existing workflows as LLM tools
        ↓
   src/mcp_manager.py     ← GitHub + Email MCP (already built)
        ↓
   src/firebase_store.py  ← Firestore read/write (memory + history)
```

**Do not call the LLM on every CI poll.** Scheduler stays as-is; the agent is for on-demand and smart requests.

---

## Firebase collections (schema)

Design Firestore collections up front:

```
/agent_sessions/{sessionId}
  - created_at: timestamp
  - updated_at: timestamp
  - title: string (optional, first user message)

/agent_sessions/{sessionId}/messages/{messageId}
  - role: "user" | "assistant" | "tool"
  - content: string
  - tool_name: string | null
  - tool_result: object | null
  - created_at: timestamp

/agent_runs/{runId}
  - session_id: string
  - model: string
  - prompt_tokens: number
  - completion_tokens: number
  - tools_called: array
  - success: boolean
  - error: string | null
  - created_at: timestamp

/workflow_history/{entryId}
  - workflow: "ci_alert" | "daily_digest" | "pr_events" | ...
  - status: "success" | "failure"
  - summary: string
  - metadata: object
  - created_at: timestamp
```

Local `logs/state.json` can remain for CI dedup; Firebase stores **agent memory and audit history**.

---

## Sub-steps (implement one at a time)

### 11.1 — OpenRouter API client

**Files:** `src/llm_client.py`, update `requirements.txt`, `.env.example`

**Tasks:**
- Add `openrouter` (or `httpx` + raw API) to `requirements.txt`
- Add env vars:
  ```env
  OPENROUTER_API_KEY=sk-or-v1-...
  OPENROUTER_MODEL=openrouter/free
  ```
- Create `src/llm_client.py`:
  - `chat(messages: list) -> str` — simple completion
  - Handle 429 rate limits with retry/backoff
  - Never log the API key

**Test:**
```bash
python src/main.py llm-test
# Expected: short response from OpenRouter
```

**Done when:** `llm-test` returns a model response without errors.

---

### 11.2 — Firebase connection

**Files:** `src/firebase_store.py`, `config/firebase-service-account.json` (gitignored), update `.gitignore`

**Tasks:**
- Add `firebase-admin` to `requirements.txt`
- Add env vars:
  ```env
  FIREBASE_PROJECT_ID=your-project-id
  FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
  ```
- Create `src/firebase_store.py`:
  - `init_firebase()` — connect once using service account
  - `save_message(session_id, role, content, ...)`
  - `get_session_messages(session_id, limit=50)`
  - `log_agent_run(model, tokens, tools_called, success)`
  - `log_workflow_history(workflow, status, summary, metadata)`

**Test:**
```bash
python src/main.py firebase-test
# Expected: writes + reads a test document in Firestore
```

**Done when:** Test message appears in Firebase Console → Firestore.

---

### 11.3 — Natural language CLI (`ask`)

**Files:** `src/agent_chat.py`, update `src/main.py`

**Tasks:**
- Add command:
  ```bash
  python src/main.py ask "What is the status of my repo?"
  ```
- Flow:
  1. Load settings + OpenRouter client
  2. Create or resume `session_id` (flag: `--session <id>`)
  3. Load prior messages from Firestore
  4. Send user message to LLM (no tools yet)
  5. Save user + assistant messages to Firestore
  6. Print response

**Done when:** Multi-turn chat works with history loaded from Firebase:
```bash
python src/main.py ask "How many open PRs do I have?"
python src/main.py ask --session <id> "Email me a summary"
```

---

### 11.4 — Agent tools (wrap existing workflows)

**Files:** `src/agent_tools.py`

Expose existing Python functions as OpenAI-style tool schemas for the LLM:

| Tool name | Maps to |
|-----------|---------|
| `fetch_github_summary` | `fetch_github_data()` |
| `run_ci_alert` | `run_ci_alert(dry_run=False)` |
| `run_ci_alert_preview` | `run_ci_alert(dry_run=True)` |
| `send_daily_digest` | `run_daily_digest(send=True)` |
| `preview_daily_digest` | `run_daily_digest(dry_run=True)` |
| `send_test_email` | `send_test_email()` |
| `check_pr_events` | `check_pr_events()` |

Each tool:
- Has a JSON schema (`name`, `description`, `parameters`)
- Has an `execute(**kwargs)` that calls the real workflow
- Logs result to `workflow_history` in Firestore

**Done when:** Tool schemas list correctly:
```bash
python src/main.py agent-tools
```

---

### 11.5 — Agent loop (think → act → observe)

**Files:** `src/agent_loop.py`, update `src/main.py`

**Tasks:**
- Implement the standard agent loop:
  1. User message → OpenRouter with `tools` parameter
  2. If model returns `tool_calls` → execute via `agent_tools.py`
  3. Append tool result to messages → call OpenRouter again
  4. Repeat until model returns text (max 5 iterations)
  5. Log full run to Firestore `agent_runs`

- Upgrade `ask` command to use agent loop when tools are needed

**Test:**
```bash
python src/main.py ask "Check CI failures and tell me what you find"
python src/main.py ask "Send me today's digest email"
python src/main.py ask --dry-run "What would the digest contain?"
```

**Done when:** Agent calls the right tool and returns a natural language summary; run logged in Firestore.

---

### 11.6 — Guardrails + human confirmation

**Files:** `src/agent_guardrails.py`

**Tasks:**
- **Sensitive tools** require confirmation before execution:
  - `send_daily_digest`, `run_ci_alert`, `send_test_email`, merge/reject actions
- Add `--yes` flag to skip confirmation (for scripts)
- Without `--yes`, print preview and ask: `Proceed? [y/N]`
- Log approval/denial in Firestore

**Done when:**
```bash
python src/main.py ask "Send digest now"
# Prompts for confirmation unless --yes
```

---

### 11.7 — Observability

**Files:** extend `src/app_logging.py`, `src/firebase_store.py`

**Tasks:**
- Log every LLM call: model, latency, token usage, tools used
- CLI command to view recent runs from Firebase:
  ```bash
  python src/main.py agent-history
  python src/main.py agent-history --session <id>
  ```
- Keep `logs/app.log` for local debugging; Firestore for durable audit trail

**Done when:** `agent-history` shows past sessions and tool calls from Firestore.

---

### 11.8 — Config + docs

**Files:** `config/config.yaml`, `README.md`, `.env.example`, `scripts/test_step11.py`

**Add to `config/config.yaml`:**
```yaml
agent:
  model: "openrouter/free"
  max_tool_iterations: 5
  require_confirmation: true
```

**Update README** with:
- OpenRouter setup
- Firebase setup
- New CLI commands (`ask`, `llm-test`, `firebase-test`, `agent-history`)
- Free tier rate limits (50 req/day without credits)
- Note: scheduler still runs without LLM

**Done when:** Another developer can set up agent + Firebase from README alone.

---

## New dependencies

Add to `requirements.txt` as each sub-step is implemented:

```
openrouter          # 11.1 — LLM client
firebase-admin      # 11.2 — Firestore
```

---

## New environment variables

Add to `.env.example`:

```env
# OpenRouter — https://openrouter.ai/keys
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free

# Firebase Firestore
FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
```

---

## New CLI commands (end state)

```bash
python src/main.py llm-test              # 11.1 — test OpenRouter connection
python src/main.py firebase-test         # 11.2 — test Firestore read/write
python src/main.py ask "..."             # 11.3+ — natural language agent
python src/main.py ask --session <id>    # resume conversation
python src/main.py ask --yes "..."       # skip confirmation for sends
python src/main.py agent-tools           # 11.4 — list available agent tools
python src/main.py agent-history         # 11.7 — view runs from Firebase
```

---

## Demo checklist

- [ ] `llm-test` returns a response from OpenRouter free model
- [ ] `firebase-test` writes and reads from Firestore
- [ ] `ask "How many open PRs?"` returns accurate data via tools
- [ ] `ask "Send digest"` asks for confirmation, then sends email
- [ ] Conversation history persists across CLI restarts (Firebase)
- [ ] `agent-history` shows logged runs
- [ ] Scheduler still works independently (`run-scheduler`)
- [ ] No secrets printed to console or committed to git

---

## Done When (Step 11 complete)

- Natural-language `ask` command works with tool calling
- Agent uses existing MCP workflows (not reimplemented)
- All conversation + run history stored in **Firebase Firestore**
- Sensitive actions require confirmation
- README documents OpenRouter + Firebase setup
- `scripts/test_step11.py` passes

---

## Rate limits & production notes

| Concern | Guidance |
|---------|----------|
| Free OpenRouter tier | ~50 requests/day — use agent on-demand, not per CI poll |
| Firebase test mode | Lock Firestore rules before any shared/production use |
| Service account JSON | Never commit — keep in `.gitignore` |
| Scheduler | Keep `run-scheduler` for digest/CI — do not replace with LLM polling |
| Optional upgrade | Add $10 OpenRouter credits → 1,000 free requests/day |

---

## Suggested folder additions

```
mcp-client/
├── src/
│   ├── llm_client.py          # 11.1 OpenRouter wrapper
│   ├── firebase_store.py      # 11.2 Firestore CRUD
│   ├── agent_tools.py         # 11.4 workflow tools for LLM
│   ├── agent_loop.py          # 11.5 think → act → observe
│   ├── agent_chat.py          # 11.3 CLI chat interface
│   └── agent_guardrails.py    # 11.6 confirmations
├── config/
│   └── firebase-service-account.json   # gitignored
└── scripts/
    └── test_step11.py
```

---

## Next Step

Start with **11.1 only** — do not implement everything at once.

→ When 11.1 passes, move to **11.2** (Firebase), then **11.3**, and so on.
