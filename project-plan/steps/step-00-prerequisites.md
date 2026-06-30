# Step 0 — Prerequisites

**Goal:** Have accounts, credentials, and tools ready before writing code.

**Estimated time:** 1–2 hours

---

## Tasks

### 1. GitHub
- [ ] Confirm you have a GitHub repo to monitor
- [ ] Note repo owner and name (e.g. `your-username/mcp-client`)
- [ ] Create a **Personal Access Token** at https://github.com/settings/tokens
  - Scopes needed: `repo`, `workflow`
- [ ] Save token securely (you will put it in `.env` later)

### 2. Email
- [ ] Choose an email account (Gmail, Outlook, etc.)
- [ ] Enable IMAP access
- [ ] Create an **app password** (not your main password)
- [ ] Note SMTP host, port, IMAP host, port

**Gmail example:**
- SMTP: `smtp.gmail.com:587`
- IMAP: `imap.gmail.com:993`

### 3. Software
- [ ] Python 3.10 or higher: `python3 --version`
- [ ] Node.js 18+: `node --version`
- [ ] Docker (optional, for GitHub MCP): `docker --version`
- [ ] Git: `git --version`

---

## Done When

- You can log into GitHub and see your repo
- You can send/receive email from your account
- `python3 --version` shows 3.10+
- `node --version` works

---

## Next Step

→ [Step 1 — Basic Project](./step-01-basic-project.md)
