# Step 0 Workbook — Fill This In

Use this file to record your setup. **Do not put passwords or tokens here** — only in `.env` later.

---

## 1. GitHub

| Item | Your value |
|------|------------|
| Repo owner (username or org) | `shelarrohit45` |
| Repo name | `MCP-Client` |
| Full repo path (`owner/repo`) | `shelarrohit45/MCP-Client` |
| PAT created? (yes/no) | |
| PAT scopes (`repo`, `workflow`) | |

**Create token:** https://github.com/settings/tokens → **Generate new token (classic)** or **Fine-grained token**

Fine-grained (recommended):
- Repository access: Only select repositories → pick your repo
- Permissions: Contents (Read), Issues (Read), Pull requests (Read), Actions (Read), Metadata (Read)

---

## 2. Email (static sender → receiver)

| Item | Your value |
|------|------------|
| Sender email (SMTP — sends alerts) | `shelarrohit78@gmail.com` |
| Receiver email (gets all alerts/digests) | `rohitluckyrs45@gmail.com` |
| Provider (Gmail / Outlook / other) | |
| Sender app password in `.env`? (yes/no) | |

Configured in `config/config.yaml`:
```yaml
email:
  sender: "your-sender@gmail.com"
  receiver: "your-receiver@gmail.com"
```

**Gmail app password (sender only):** https://myaccount.google.com/apppasswords

---

## 3. Software (checked on your Mac)

| Tool | Required | Your machine | Status |
|------|----------|--------------|--------|
| Python 3.10+ | Yes | 3.12 via Homebrew (`/opt/homebrew/bin/python3.12`) | OK — use this in Step 1 |
| Node.js 18+ | Yes | v26.0.0 | OK |
| Git | Yes | 2.50.1 | OK |
| Docker | Optional | Not installed | Skip for now — use GitHub MCP binary in Step 3 |

---

## Step 0 Checklist

- [x] GitHub repo confirmed (`shelarrohit45/MCP-Client`)
- [x] Repo owner/name written above
- [ ] GitHub PAT created and saved securely
- [x] Email account chosen (Gmail)
- [x] Static sender/receiver set in `config/config.yaml`
- [x] Sender app password in `.env`
- [x] Software check passed (run `python3 scripts/check_prerequisites.py`)

---

## Next

When all boxes are checked → [Step 1 — Basic Project](../steps/step-01-basic-project.md)
