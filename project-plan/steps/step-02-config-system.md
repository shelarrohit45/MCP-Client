# Step 2 — Config System

**Goal:** Load settings from YAML and environment variables (no hardcoded secrets).

**Estimated time:** 1–2 hours

---

## Tasks

### 1. Create `config/config.yaml`
```yaml
github:
  owner: "your-username"
  repo: "your-repo-name"

email:
  recipients:
    - "you@example.com"

schedule:
  digest_time: "09:00"
  ci_check_interval_minutes: 30
```

### 2. Create `.env.example`
```env
GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
EMAIL_ADDRESS=you@example.com
EMAIL_PASSWORD=your_app_password_here
```

Copy to `.env` and fill in real values (do not commit `.env`).

### 3. Create `src/config.py`
- Load `config/config.yaml` with PyYAML
- Load `.env` with `python-dotenv`
- Expose: `github_owner`, `github_repo`, `email_recipients`, `github_token`
- Never print secrets to console

### 4. Update `src/main.py`
- Import config
- Print repo name and recipient count (not tokens/passwords)

---

## Done When

- App prints repo owner/name and number of recipients
- Secrets are loaded from `.env` but not displayed
- Missing `.env` shows a clear error message

---

## Commands
```bash
python src/main.py
```

---

## Next Step

→ [Step 3 — GitHub MCP Connect](./step-03-github-mcp-connect.md)
