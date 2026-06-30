# Step 0 Workbook — Fill This In

Use this file to record your setup. **Do not put passwords or tokens here** — only in `.env` later.

---

## 1. GitHub

| Item | Your value |
|------|------------|
| Repo owner (username or org) | |
| Repo name | |
| Full repo path (`owner/repo`) | |
| PAT created? (yes/no) | |
| PAT scopes (`repo`, `workflow`) | |

**Create token:** https://github.com/settings/tokens → **Generate new token (classic)** or **Fine-grained token**

Fine-grained (recommended):
- Repository access: Only select repositories → pick your repo
- Permissions: Contents (Read), Issues (Read), Pull requests (Read), Actions (Read), Metadata (Read)

---

## 2. Email

| Item | Your value |
|------|------------|
| Provider (Gmail / Outlook / other) | |
| Email address | |
| IMAP host | |
| IMAP port | |
| SMTP host | |
| SMTP port | |
| App password created? (yes/no) | |

**Gmail:** https://myaccount.google.com/apppasswords (requires 2FA enabled)

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

- [ ] GitHub repo confirmed
- [ ] Repo owner/name written above
- [ ] GitHub PAT created and saved securely
- [ ] Email account chosen
- [ ] IMAP enabled
- [ ] App password created and saved securely
- [ ] Software check passed

---

## Next

When all boxes are checked → [Step 1 — Basic Project](../steps/step-01-basic-project.md)
