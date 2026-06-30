# Step 9 — Logging + Duplicate Protection

**Goal:** Make the app reliable for repeated scheduled runs.

**Estimated time:** 2–3 hours

---

## Tasks

### 1. Structured logging
- Log to `logs/app.log`
- Log: timestamp, workflow name, tool calls, success/failure
- Use Python `logging` module

### 2. State file
Create `logs/state.json`:
```json
{
  "last_ci_alert_at": "2026-06-30T10:00:00Z",
  "alerted_run_ids": ["12345678", "87654321"]
}
```

### 3. Duplicate prevention
- Before sending CI alert, check if run ID was already alerted
- Skip send if already in `alerted_run_ids`
- Update state after successful send

### 4. Error handling
- Clear messages for: bad token, SMTP failure, MCP timeout
- Log errors without crashing the whole app

---

## Done When

- Running `ci-alert` twice does not send duplicate emails
- `logs/app.log` records each run
- `logs/state.json` updates after alerts

---

## Next Step

→ [Step 10 — Scheduler + Docs](./step-10-scheduler-docs.md)
