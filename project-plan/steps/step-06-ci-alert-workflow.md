# Step 6 — CI Failure Alert (First Complete Workflow)

**Goal:** End-to-end feature — detect failed CI and send alert email.

**Estimated time:** 3–4 hours

---

## Tasks

### 1. Create `src/workflows/ci_alert.py`
- Fetch failed workflow runs (last 24h)
- If none: print `"No CI failures"` and exit
- If found: build alert message with:
  - Repo name
  - Workflow name
  - Branch
  - Author
  - Link to failed run

### 2. Send alert via Email MCP
- Plain text body for now (HTML comes in Step 7)
- Subject: `[CI FAILED] {repo} — {workflow_name}`

### 3. Add `--dry-run` flag
- Print email content to terminal
- Do not send when `--dry-run` is set

### 4. Add CLI command
```bash
python src/main.py ci-alert --dry-run
python src/main.py ci-alert
```

---

## Done When

- Dry-run shows correct alert content for a real failure
- Live run sends email to your inbox
- No alert sent when there are no failures

---

## Next Step

→ [Step 7 — HTML Templates](./step-07-html-templates.md)
