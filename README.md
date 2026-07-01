# MCP DevOps Client

A **local Python automation client** that monitors a GitHub repository and sends email alerts and digests — with an optional **natural language agent** powered by OpenRouter and Firebase.

**Repository:** [shelarrohit45/MCP-Client](https://github.com/shelarrohit45/MCP-Client)

---

## Project goal

Build a DevOps assistant that:

1. Connects to **GitHub** and **Email** through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
2. Automates **CI failure alerts**, **daily digests**, and **PR notifications**
3. Runs **locally** without AWS or custom cloud hosting
4. Adds an optional **LLM agent** (`ask`) that reuses the same workflows — with chat memory in Firestore

No AWS required. The scheduler works without the agent layer.

---

## What we built (Steps 0–11)

| Step | Feature | Key files |
|------|---------|-----------|
| **0** | Prerequisites check | `scripts/check_prerequisites.py` |
| **1** | Project structure, venv, CLI | `src/main.py`, `requirements.txt` |
| **2** | YAML + `.env` configuration | `src/config.py`, `config/config.yaml` |
| **3** | GitHub MCP connection | `src/mcp_manager.py`, `bin/github-mcp-server` |
| **4** | Fetch PRs, CI status, issues | `src/github_fetch.py` |
| **5** | Email MCP connection | `src/email_client.py`, `@codefuturist/email-mcp` |
| **6** | CI failure alert workflow | `src/workflows/ci_alert.py` |
| **7** | Jinja2 HTML email templates | `templates/`, `src/template_renderer.py` |
| **8** | Daily digest email | `src/workflows/daily_digest.py` |
| **9** | Logging + duplicate protection | `src/app_logging.py`, `logs/state.json` |
| **10** | APScheduler automation | `src/scheduler.py`, `run-scheduler` |
| **11** | OpenRouter agent + Firebase memory | `src/agent_*.py`, `src/llm_client.py`, `src/firebase_store.py` |

**Detailed docs:**

- [Architecture & design patterns](docs/ARCHITECTURE.md)
- [Firebase setup, schema & testing](docs/FIREBASE.md)
- [Full testing guide](docs/TESTING.md)
- [Build plan & checklist](project-plan/README.md)

---

## Tech stack — what we used and why

| Technology | Role | Why |
|------------|------|-----|
| **Python 3.12** | Main application | MCP SDK, workflows, CLI |
| **GitHub MCP Server** | GitHub integration | Official MCP tool surface; no custom API glue |
| **Email MCP** (`@codefuturist/email-mcp`) | Send email via MCP | Standardized email tools; Node/npm dependency only |
| **httpx** | OpenRouter HTTP client | Async-capable, simple REST for LLM API |
| **OpenRouter** | LLM provider | Multi-model API; free tier for development |
| **Firebase Firestore** | Agent memory & audit | Durable sessions, runs, workflow history |
| **firebase-admin** | Server-side Firestore | Service account auth (industry standard for backends) |
| **APScheduler** | Cron-like scheduling | Daily digest + periodic CI checks in-process |
| **Jinja2** | HTML emails | Separation of template and data |
| **PyYAML + python-dotenv** | Configuration | Non-secrets in YAML; secrets in `.env` (12-factor) |
| **GitHub Actions** | CI | Unit tests on every branch push |

---

## What it does

- Fetches open PRs, CI status, issues, and releases from GitHub
- Sends **CI failure alerts** when checks fail (with duplicate protection)
- Sends a **daily digest** email summarizing repo activity
- Notifies on **PR events** (created, merged, approved, CI passed/failed)
- **Merge/Reject links** in PR emails via a local action server
- **Natural language agent** (`ask`) with tool calling, confirmations, and Firebase memory

---

## Quick start

```bash
# 1. Clone and enter project
cd mcp-client

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install MCP servers
./scripts/install_github_mcp.sh
./scripts/install_email_mcp.sh

# 4. Configure
cp config/config.example.yaml config/config.yaml   # if needed
cp .env.example .env
# Edit config/config.yaml (repo, emails, schedule)
# Edit .env (GITHUB_PERSONAL_ACCESS_TOKEN, EMAIL_PASSWORD, etc.)

# 5. Verify
python scripts/check_prerequisites.py
python src/main.py list-github-tools
python src/main.py list-email-tools
python src/main.py send-test-email
```

---

## Run automation (keep terminal open)

```bash
source venv/bin/activate
python src/main.py run-scheduler
```

- **Daily digest** at `schedule.digest_time` (default `09:00` local)
- **CI alert check** every `schedule.ci_check_interval_minutes` (default 30)

Press `Ctrl+C` to stop. Logs: `logs/app.log`

```bash
# Optional: watch logs in another terminal
tail -f logs/app.log
```

---

## Testing

### Fast automated tests (recommended first)

```bash
source venv/bin/activate
chmod +x scripts/run_all_tests.sh
./scripts/run_all_tests.sh --unit
```

### Full local tests (needs `.env` + MCP servers)

```bash
./scripts/run_all_tests.sh
```

### Live smoke test

```bash
python scripts/check_prerequisites.py
python src/main.py list-github-tools
python src/main.py send-test-email
python src/main.py ci-alert --dry-run
python src/main.py digest --dry-run
python src/main.py llm-test
python src/main.py firebase-test
python src/main.py ask --dry-run "How many open PRs?"
python src/main.py agent-history
```

### Firebase testing

```bash
python src/main.py firebase-test
python src/main.py ask --dry-run "How many open PRs?"
python src/main.py agent-history
```

Then open **Firebase Console → Firestore → Data** to see `agent_sessions`, `agent_runs`, `workflow_history`.

Full details: [docs/TESTING.md](docs/TESTING.md) and [docs/FIREBASE.md](docs/FIREBASE.md).

### CI (every branch, not only main)

GitHub Actions runs on every `push` and `pull_request`. Add secrets `GITHUB_PERSONAL_ACCESS_TOKEN` and `EMAIL_PASSWORD` for integration tests.

See [docs/TESTING.md#ci-github-actions](docs/TESTING.md#ci-github-actions).

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.12+** | `python3 --version` |
| **Node.js 18+** | For Email MCP |
| **GitHub PAT** | [Create token](https://github.com/settings/tokens) — `repo` scope |
| **Gmail app password** | [Google App Passwords](https://myaccount.google.com/apppasswords) |
| **OpenRouter API key** | Optional — [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Firebase project** | Optional — [Firebase Console](https://console.firebase.google.com) |

---

## Configuration

### `config/config.yaml`

| Section | Key | Description |
|---------|-----|-------------|
| `github` | `owner`, `repo` | Target repository |
| `email` | `sender`, `receiver` | From/to addresses |
| `schedule` | `digest_time` | Daily digest (`09:00` = 9 AM local) |
| `schedule` | `ci_check_interval_minutes` | CI check interval |
| `pr_notify` | `check_interval_minutes` | PR watch interval |
| `agent` | `model` | OpenRouter model (overridden by `.env`) |
| `agent` | `max_tool_iterations` | Max tool rounds per `ask` |
| `agent` | `require_confirmation` | Prompt before sensitive agent actions |

### `.env` (secrets — never commit)

| Variable | Description |
|----------|-------------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub PAT |
| `EMAIL_PASSWORD` | Gmail app password |
| `ACTION_SECRET` | PR action link secret (`openssl rand -hex 32`) |
| `ACTION_BASE_URL` | Base URL for Merge/Reject links |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Default `openrouter/free` |
| `FIREBASE_PROJECT_ID` | Firebase project id |
| `FIREBASE_CREDENTIALS_PATH` | Service account JSON path |

### OpenRouter

1. Key at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Add to `.env`, verify: `python src/main.py llm-test`
3. Free tier: ~**50 requests/day** without credits; HTTP 429 retried with backoff

### Firebase

1. Create project + enable **Firestore**
2. Download service account JSON → `config/firebase-service-account.json`
3. Set `FIREBASE_PROJECT_ID` in `.env`
4. Verify: `python src/main.py firebase-test`

Full schema and console guide: [docs/FIREBASE.md](docs/FIREBASE.md)

---

## CLI commands

### GitHub & email

```bash
python src/main.py list-github-tools
python src/main.py fetch-github
python src/main.py list-email-tools
python src/main.py send-test-email
```

### Workflows

```bash
python src/main.py ci-alert              # Send CI failure alerts
python src/main.py ci-alert --dry-run
python src/main.py digest --dry-run      # Preview digest
python src/main.py digest --send         # Send digest
python src/main.py pr-notify
python src/main.py pr-events
python src/main.py pr-watch
```

### PR actions & scheduler

```bash
python src/main.py action-server
python src/main.py run-scheduler         # Keep terminal open
```

### Agent (OpenRouter + Firebase)

```bash
python src/main.py llm-test
python src/main.py firebase-test
python src/main.py ask "How many open PRs?"
python src/main.py ask --session <id> "Follow up..."
python src/main.py ask --dry-run "Preview the digest"
python src/main.py ask --yes "Send digest now"
python src/main.py agent-tools
python src/main.py agent-history
python src/main.py agent-history --session <id>
```

Sensitive tools prompt `Proceed? [y/N]` unless `--yes` or `agent.require_confirmation: false`.

---

## Architecture

```
User / Scheduler
       │
       ▼
   main.py (CLI)
       │
       ├── workflows/ ──► GitHub MCP ──► GitHub API
       │              └── Email MCP ──► Gmail
       │
       └── ask ──► agent_loop ──► OpenRouter
                      │              │
                      ├── agent_tools (wraps workflows)
                      ├── agent_guardrails (confirm sends)
                      └── firebase_store ──► Firestore
```

Full diagram and patterns: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Project layout

```
mcp-client/
├── docs/
│   ├── ARCHITECTURE.md      # Design, data flows, patterns
│   ├── FIREBASE.md          # Firestore schema & testing
│   └── TESTING.md           # How and where to test
├── src/
│   ├── main.py              # CLI entry point
│   ├── config.py            # Settings loader
│   ├── mcp_manager.py       # GitHub + Email MCP
│   ├── scheduler.py         # APScheduler
│   ├── workflows/           # ci_alert, daily_digest, pr_*
│   ├── llm_client.py        # OpenRouter
│   ├── firebase_store.py    # Firestore
│   └── agent_*.py           # Agent layer
├── config/
│   ├── config.yaml
│   └── firebase-service-account.json  # gitignored
├── templates/               # Jinja2 email HTML
├── logs/                    # app.log, state.json (gitignored)
├── scripts/                 # install, test, run_all_tests.sh
├── .github/workflows/ci.yml # CI on all branches
└── project-plan/            # Step-by-step build plan
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| GitHub MCP not found | `./scripts/install_github_mcp.sh` |
| Private repo 403 | PAT needs `repo` scope |
| Email MCP failed | Check `EMAIL_PASSWORD`; run `list-email-tools` |
| Duplicate CI alerts | By design — see `logs/state.json` |
| Scheduler not running | Keep terminal open or use cron |
| `llm-test` 401 | Check `OPENROUTER_API_KEY` |
| `llm-test` 429 | Free tier limit; wait or add credits |
| `firebase-test` fails | Create Firestore DB; check project id + JSON path |
| `ask` fails | Run `firebase-test` first |
| Agent sent without prompt | You used `--yes` or disabled confirmation |

```bash
tail -f logs/app.log
```

---

## License

Private project — adjust as needed.
