# MCP DevOps Client

A Python automation client that connects to **GitHub MCP** and **Email MCP** to monitor your repository and send email alerts and digests.

## What it does

- Fetches open PRs, CI status, issues, and releases from GitHub
- Sends **CI failure alerts** when checks fail (with duplicate protection)
- Sends a **daily digest** email summarizing repo activity
- Notifies on **PR events** (created, merged, approved, CI passed/failed, and more)
- Supports **Merge/Reject links** in PR notification emails via a local action server

No AWS or cloud hosting required — runs locally on your machine.

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.12+** | `python3 --version` |
| **Node.js 18+** | For Email MCP (`npx` / `node`) |
| **GitHub PAT** | [Create token](https://github.com/settings/tokens) with `repo` scope (write for Merge/Reject) |
| **Gmail app password** | For the sender account ([Google App Passwords](https://myaccount.google.com/apppasswords)) |

### Install MCP servers

```bash
./scripts/install_github_mcp.sh
./scripts/install_email_mcp.sh
```

---

## Quick start

```bash
# 1. Clone and enter project
cd mcp-client

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp config/config.example.yaml config/config.yaml
cp .env.example .env
# Edit config/config.yaml (repo, email addresses)
# Edit .env (GITHUB_PERSONAL_ACCESS_TOKEN, EMAIL_PASSWORD, ACTION_SECRET)

# 4. Set up Email MCP config
python scripts/setup_email_mcp_config.py   # if available, or run install_email_mcp.sh

# 5. Verify connections
python src/main.py list-github-tools
python src/main.py list-email-tools
python src/main.py send-test-email
```

---

## Configuration

### `config/config.yaml`

| Section | Key | Description |
|---------|-----|-------------|
| `github` | `owner`, `repo` | Target repository |
| `email` | `sender`, `receiver` | From/to addresses |
| `schedule` | `digest_time` | Daily digest time (`09:00` = 9 AM local) |
| `schedule` | `ci_check_interval_minutes` | How often to check CI failures |
| `pr_notify` | `check_interval_minutes` | PR watch polling interval |

### `.env` (secrets — never commit)

| Variable | Description |
|----------|-------------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub PAT |
| `EMAIL_PASSWORD` | Gmail app password for sender |
| `ACTION_SECRET` | Random secret for PR action links (`openssl rand -hex 32`) |
| `ACTION_BASE_URL` | Base URL for Merge/Reject links (use ngrok for phone) |
| `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORT` | SMTP settings (Gmail defaults) |
| `EMAIL_IMAP_HOST` / `EMAIL_IMAP_PORT` | IMAP settings (Gmail defaults) |

### Email MCP config

Email credentials are written to `config/email-mcp/config.toml` (gitignored) by the setup script.

---

## CLI commands

### GitHub

```bash
python src/main.py list-github-tools    # List GitHub MCP tools
python src/main.py fetch-github         # Fetch open PRs + failed CI sample
```

### Email

```bash
python src/main.py list-email-tools     # List Email MCP tools
python src/main.py send-test-email      # Send a test email
```

### CI alerts

```bash
python src/main.py ci-alert             # Send alert for new CI failures (last 24h)
python src/main.py ci-alert --dry-run   # Preview without sending
```

Duplicate alerts are skipped automatically via `logs/state.json`.

### Daily digest

```bash
python src/main.py digest --dry-run     # Preview digest HTML
python src/main.py digest --send        # Send digest email
```

### PR notifications

```bash
python src/main.py pr-notify            # Notify for new open PRs
python src/main.py pr-notify --dry-run
python src/main.py pr-events            # Check all PR events once
python src/main.py pr-watch             # Poll PR events continuously (every 5 min)
python src/main.py pr-watch --interval 10
```

### PR action server (Merge/Reject from email)

```bash
python src/main.py action-server        # Start HTTP server for email links
python src/main.py check-action-server  # Verify server is reachable
```

### Scheduler (automation)

```bash
python src/main.py run-scheduler
```

Runs in the foreground:
- **Daily digest** at `schedule.digest_time` (default 09:00)
- **CI alert check** every `schedule.ci_check_interval_minutes` (default 30)

Press `Ctrl+C` to stop. Logs go to `logs/app.log`.

#### Alternative: system cron

```cron
0 9 * * * cd /path/to/mcp-client && venv/bin/python src/main.py digest --send
*/30 * * * * cd /path/to/mcp-client && venv/bin/python src/main.py ci-alert
```

---

## Project layout

```
mcp-client/
├── src/
│   ├── main.py              # CLI entry point
│   ├── config.py            # Settings loader
│   ├── mcp_manager.py       # GitHub + Email MCP connections
│   ├── scheduler.py         # APScheduler automation
│   ├── workflows/           # ci_alert, daily_digest, pr_events, pr_notify
│   └── ...
├── config/
│   ├── config.yaml          # Non-secret settings
│   └── email-mcp/           # Email MCP config (gitignored)
├── templates/               # Jinja2 HTML email templates
├── logs/                    # app.log, state.json (gitignored)
├── scripts/                 # Install + test scripts
└── requirements.txt
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **GitHub MCP not found** | Run `./scripts/install_github_mcp.sh` or set `GITHUB_MCP_SERVER_PATH` |
| **Private repo 403/empty data** | PAT needs `repo` scope with read access |
| **Email MCP connection failed** | Check `EMAIL_PASSWORD` (Gmail app password), run `list-email-tools` |
| **Merge/Reject 403** | PAT needs **Pull requests** + **Contents** write |
| **Email links don't work on phone** | Start `action-server` and set `ACTION_BASE_URL` to an ngrok HTTPS URL |
| **Duplicate CI alerts** | Working as designed — cleared via `logs/state.json` |
| **No releases in digest** | Normal if the repo has no GitHub releases |
| **Scheduler not running** | Keep terminal open or use cron; check `logs/app.log` |

### View logs

```bash
tail -f logs/app.log
```

### Run step verification tests

```bash
python scripts/test_step01.py
# ... through ...
python scripts/test_step10.py
```

---

## License

Private project — adjust as needed.
