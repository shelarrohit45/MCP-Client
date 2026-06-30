# Step 8 — Daily Digest Workflow

**Goal:** Send a summary email of repo activity once per day.

**Estimated time:** 3–4 hours

---

## Tasks

### 1. Create `src/workflows/daily_digest.py`

Collect from GitHub MCP:
- Open PRs (count + titles + authors)
- Failed CI runs (last 24h)
- Successful CI runs (last 24h)
- Open issues (count)
- Latest release (if any)

### 2. Create `templates/digest.html`
Sections:
- Summary stats (PRs, issues, CI)
- Open PRs table
- CI failures list
- Latest release info

### 3. Add CLI commands
```bash
python src/main.py digest --dry-run
python src/main.py digest --send
```

### 4. Subject line
`[Daily Digest] {owner}/{repo} — {date}`

---

## Done When

- Dry-run shows full digest preview
- Send delivers formatted email to recipients
- Works even when some sections are empty (e.g. no failures)

---

## Next Step

→ [Step 9 — Logging + Dedup](./step-09-logging-dedup.md)
