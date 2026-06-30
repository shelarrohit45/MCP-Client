# Step 5 — Connect Email MCP

**Goal:** Connect to Email MCP and send a test email.

**Estimated time:** 2–3 hours

---

## Tasks

### 1. Configure Email MCP server
```json
{
  "mcpServers": {
    "email": {
      "command": "npx",
      "args": ["-y", "@codefuturist/email-mcp"]
    }
  }
}
```

### 2. Set up Email MCP config
Run setup wizard or create config manually:
```bash
npx @codefuturist/email-mcp setup
```
Config location: `~/.config/email-mcp/config.toml`

### 3. Extend `src/mcp_manager.py`
- Add Email MCP connection (separate from GitHub)
- List Email MCP tools
- Call send-email tool

### 4. Send test email
- Subject: `MCP Test`
- Body: `Hello from MCP client`
- Recipient: your own email from config

### 5. Add CLI commands
```bash
python src/main.py list-email-tools
python src/main.py send-test-email
```

---

## Done When

- `list-email-tools` shows email tools
- Test email arrives in your inbox
- SMTP/IMAP credentials work

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| SMTP auth failed | Use app password, not main password |
| Email MCP config missing | Run `npx @codefuturist/email-mcp setup` |
| Email in spam | Check spam folder; use plain text first |

---

## Next Step

→ [Step 6 — CI Alert Workflow](./step-06-ci-alert-workflow.md)
