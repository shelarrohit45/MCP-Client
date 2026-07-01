# Testing Guide

## Where to test

| Environment | What runs | Command / location |
|-------------|-----------|-------------------|
| **Your machine** | Full stack including live GitHub, email, Firebase | `./scripts/run_all_tests.sh` |
| **Your machine (fast)** | Code-only, no network | `./scripts/run_all_tests.sh --unit` |
| **GitHub Actions** | Unit tests on every branch push | `.github/workflows/ci.yml` |
| **GitHub Actions** | Integration tests (steps 3–9) | Same workflow, needs repo secrets |
| **Firebase Console** | Visual inspection of Firestore data | console.firebase.google.com |
| **Email inbox** | Real email delivery | `send-test-email`, `digest --send` |

## Quick start: “is everything working?”

Run in order from project root:

```bash
source venv/bin/activate

# 1. Prerequisites
python scripts/check_prerequisites.py

# 2. Automated code tests (fast, ~30s)
chmod +x scripts/run_all_tests.sh
./scripts/run_all_tests.sh --unit

# 3. Live connections
python src/main.py list-github-tools
python src/main.py list-email-tools
python src/main.py send-test-email

# 4. Workflow previews (no send)
python src/main.py fetch-github
python src/main.py ci-alert --dry-run
python src/main.py digest --dry-run

# 5. Agent + Firebase
python src/main.py llm-test
python src/main.py firebase-test
python src/main.py ask --dry-run "How many open PRs?"
python src/main.py agent-history
```

## Test suites

### Unit tests (no live MCP / network)

```bash
./scripts/run_all_tests.sh --unit
```

Runs: `test_step01`, `test_step02`, `test_step10`, `test_step11` (+ all Step 11 sub-tests).

### Live integration tests

```bash
./scripts/run_all_tests.sh --live
```

Requires:
- `.env` with real credentials
- `./scripts/install_github_mcp.sh`
- `./scripts/install_email_mcp.sh`

Runs: `check_prerequisites`, `test_step03` through `test_step09`.

### Full suite

```bash
./scripts/run_all_tests.sh
```

Unit + live together.

### Individual step tests

```bash
python scripts/test_step01.py   # Project structure
python scripts/test_step02.py   # Config loader
python scripts/test_step03.py   # GitHub MCP
python scripts/test_step04.py   # GitHub data fetch
python scripts/test_step05.py   # Email MCP
python scripts/test_step06.py   # CI alert
python scripts/test_step07.py   # HTML templates
python scripts/test_step08.py   # Daily digest
python scripts/test_step09.py   # Logging + dedup
python scripts/test_step10.py   # Scheduler
python scripts/test_step11.py   # Agent layer (runs 11.1–11.7)
```

## Keep terminal running (production smoke test)

After tests pass, start the scheduler and leave it open:

```bash
python src/main.py run-scheduler
```

In another terminal, watch logs:

```bash
tail -f logs/app.log
```

## CI (GitHub Actions)

Workflow: `.github/workflows/ci.yml`

- Triggers on **every branch** `push` and on `pull_request`
- **Unit tests** — always run, no secrets
- **Integration tests** — run when `GITHUB_PERSONAL_ACCESS_TOKEN` is set in repo secrets

### One-time CI setup

GitHub repo → **Settings → Secrets and variables → Actions**:

| Secret | Required for |
|--------|----------------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Integration job |
| `EMAIL_PASSWORD` | Email MCP (optional) |

Push any branch:

```bash
git push -u origin feature/my-branch
```

Check **Actions** tab on GitHub.

## Pass criteria checklist

| Test | Pass if |
|------|---------|
| `check_prerequisites.py` | All required checks PASS |
| `run_all_tests.sh --unit` | "All test groups passed" |
| `list-github-tools` | Lists tools, no 401 |
| `send-test-email` | Email in inbox |
| `ci-alert --dry-run` | Output, no crash |
| `digest --dry-run` | HTML preview shown |
| `llm-test` | Model response returned |
| `firebase-test` | session_id + run_id printed |
| `ask --dry-run` | Answer with session id |
| `agent-history` | Shows sessions/runs |
| `run-scheduler` | Prints schedule, stays running |

## Firebase-specific tests

See [FIREBASE.md](./FIREBASE.md) for schema and console verification.

```bash
python src/main.py firebase-test
python src/main.py ask --dry-run "test question"
python src/main.py agent-history
python src/main.py agent-history --session <id>
python scripts/test_step11_2.py
python scripts/test_step11_7.py
```

Then confirm data in **Firebase Console → Firestore → Data**.
