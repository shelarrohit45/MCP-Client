# Progress Checklist

Mark each item when done. Complete steps in order.

## Step 0 — Prerequisites
- [ ] GitHub repo ready
- [ ] GitHub Personal Access Token created
- [ ] Email IMAP/SMTP credentials ready
- [ ] Python 3.10+ installed
- [ ] Node.js installed (for Email MCP)

## Step 1 — Basic Project
- [ ] Folder structure created (`src/`, `templates/`, `logs/`, `tests/`)
- [ ] Virtual environment set up
- [ ] `requirements.txt` created
- [ ] `.gitignore` created
- [ ] `python src/main.py` runs successfully

## Step 2 — Config System
- [ ] `config/config.yaml` created
- [ ] `.env.example` created
- [ ] `src/config.py` loads YAML + env
- [ ] Config prints without exposing secrets

## Step 3 — GitHub MCP Connect
- [ ] GitHub MCP server configured
- [ ] `src/mcp_manager.py` connects to GitHub MCP
- [ ] `list-github-tools` command works

## Step 4 — GitHub Data Fetch
- [ ] Open PRs fetched from repo
- [ ] Failed CI runs fetched
- [ ] Sample JSON saved to `logs/github_sample.json`

## Step 5 — Email MCP Connect
- [ ] Email MCP server configured
- [ ] Email MCP tools listed
- [ ] Test email received in inbox

## Step 6 — CI Alert Workflow
- [ ] Failed runs detected (last 24h)
- [ ] Alert email built
- [ ] `ci-alert` command works
- [ ] `--dry-run` mode works

## Step 7 — HTML Templates
- [ ] `jinja2` added to requirements
- [ ] `templates/ci_alert.html` created
- [ ] HTML alert email sends correctly

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
