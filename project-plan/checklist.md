# Progress Checklist

Mark each item when done. Complete steps in order.

## Step 0 — Prerequisites
- [x] GitHub repo ready (`shelarrohit45/MCP-Client`)
- [x] GitHub Personal Access Token created
- [x] Static sender/receiver set (`shelarrohit78@gmail.com` → `rohitluckyrs45@gmail.com`)
- [x] Python 3.10+ installed (Python 3.12 via Homebrew)
- [x] Node.js installed (for Email MCP)
- [x] `.env` created from `.env.example`
- [x] `python3 scripts/check_prerequisites.py` passes

## Step 1 — Basic Project
- [x] Folder structure created (`src/`, `templates/`, `logs/`, `tests/`)
- [x] Virtual environment set up (Python 3.12)
- [x] `requirements.txt` created
- [x] `.gitignore` created
- [x] `python src/main.py` runs successfully

## Step 2 — Config System
- [x] `config/config.yaml` created
- [x] `.env.example` created
- [x] `src/config.py` loads YAML + env
- [x] Config prints without exposing secrets

## Step 3 — GitHub MCP Connect
- [x] GitHub MCP server installed (`./scripts/install_github_mcp.sh`)
- [x] `src/mcp_manager.py` connects to GitHub MCP
- [x] `list-github-tools` command works

## Step 4 — GitHub Data Fetch
- [x] Open PRs fetched from repo
- [x] Failed CI runs fetched
- [x] Sample JSON saved to `logs/github_sample.json`

## Step 5 — Email MCP Connect
- [x] Email MCP server configured (via npx + project `.env`)
- [x] `src/mcp_manager.py` extended for Email MCP
- [x] `list-email-tools` command added
- [x] `send-test-email` command added
- [x] Test email received in inbox

## Step 6 — CI Alert Workflow
- [x] Failed runs detected (last 24h)
- [x] Alert email built
- [x] `ci-alert` command works
- [x] `--dry-run` mode works
- [ ] Live alert received when CI actually fails (run `python src/main.py ci-alert`)

## Step 7 — HTML Templates
- [x] `jinja2` added to requirements
- [x] `templates/ci_alert.html` created
- [x] `src/template_renderer.py` created
- [x] CI alert sends HTML email
- [x] `--dry-run` prints HTML preview
- [ ] HTML alert received in inbox when CI fails

## Step 8 — Daily Digest
- [ ] `src/workflows/daily_digest.py` created
- [ ] `templates/digest.html` created
- [ ] `digest --dry-run` and `digest --send` work

## Step 9 — Logging + Dedup
- [ ] App logs to `logs/app.log`
- [ ] State saved in `logs/state.json`
- [ ] Duplicate CI alerts prevented

## Step 10 — Scheduler + Docs
- [ ] Daily digest scheduled
- [ ] CI alert check scheduled
- [ ] `README.md` complete with setup guide

## Step 11 — OpenRouter Agent + Firebase
- [ ] OpenRouter API key configured (`OPENROUTER_API_KEY`)
- [x] Step 11.1 code: `src/llm_client.py` + `llm-test` command
- [ ] `python src/main.py llm-test` returns live OpenRouter response
- [ ] Firebase project + service account configured
- [x] Step 11.2 code: `src/firebase_store.py` + `firebase-test` command
- [ ] `python src/main.py firebase-test` writes to Firestore
- [x] Step 11.3 code: `src/agent_chat.py` + `ask` command
- [ ] Multi-turn `ask --session` works with Firebase history
- [ ] Firebase project + Firestore enabled
- [ ] `firebase-test` writes/reads from Firestore
- [ ] `ask` command with natural language works
- [ ] Agent tools wrap existing workflows
- [ ] Agent loop calls tools and logs to Firebase
- [ ] Confirmation required before sending emails
- [ ] `agent-history` shows past runs from Firestore
- [ ] `scripts/test_step11.py` passes
