# Step 3 — Connect GitHub MCP

**Goal:** Connect to GitHub MCP server and list available tools.

**Estimated time:** 2–3 hours

---

## Tasks

### 1. Configure GitHub MCP server

**Option A — Docker (recommended):**
```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
      }
    }
  }
}
```

**Option B — Binary:** Build from https://github.com/github/github-mcp-server

### 2. Create `src/mcp_manager.py`
- Function to spawn/connect to GitHub MCP via stdio
- Function to list all tools from the server
- Function to call a tool by name with arguments

### 3. Add CLI command in `main.py`
```bash
python src/main.py list-github-tools
```

---

## Done When

- Terminal shows a list of GitHub MCP tool names
- No authentication errors
- Connection closes cleanly

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| Docker not running | Start Docker Desktop |
| 401 Unauthorized | Check GitHub PAT scopes (`repo`, `workflow`) |
| MCP connection timeout | Verify server command in MCP config |

---

## Next Step

→ [Step 4 — GitHub Data Fetch](./step-04-github-data-fetch.md)
