# Step 10 — Scheduler + Documentation

**Goal:** Automate workflows and document the project for others.

**Estimated time:** 2–3 hours

---

## Tasks

### 1. Add scheduler

**Option A — APScheduler (in Python):**
```
apscheduler
```
- Daily digest at `config.schedule.digest_time` (e.g. 09:00)
- CI alert check every `ci_check_interval_minutes` (e.g. 30 min)

**Option B — System cron:**
```cron
0 9 * * * cd /path/to/mcp-client && venv/bin/python src/main.py digest --send
*/30 * * * * cd /path/to/mcp-client && venv/bin/python src/main.py ci-alert
```

### 2. Add scheduler CLI
```bash
python src/main.py run-scheduler    # start APScheduler loop
```

### 3. Write project `README.md`
Include:
- What the project does
- Prerequisites (GitHub PAT, email setup)
- MCP server configuration
- Environment variables
- All CLI commands
- Troubleshooting

### 4. Demo checklist
- [ ] `fetch-github` returns data
- [ ] `send-test-email` works
- [ ] `ci-alert --dry-run` shows preview
- [ ] `digest --send` delivers email
- [ ] Scheduler runs without errors

---

## Done When

- Digest and CI alert run on schedule (or cron is configured)
- README allows someone else to set up the project
- Full demo passes all checklist items

---

## Project Complete

You now have a working **GitHub + Email MCP automation client**.

### Optional future enhancements
- PR reminder workflow
- Release announcement email

→ Continue to [Step 11 — OpenRouter Agent + Firebase](./step-11-agent-openrouter-firebase.md) for the natural-language agent layer and cloud history (Firebase Firestore).
