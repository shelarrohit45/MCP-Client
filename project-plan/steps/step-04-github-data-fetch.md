# Step 4 — Fetch GitHub Data

**Goal:** Pull real data from your repo using GitHub MCP tools.

**Estimated time:** 2–3 hours

---

## Tasks

### 1. Fetch open PRs
- Call the appropriate GitHub MCP tool for listing pull requests
- Filter by your configured `owner/repo`
- Print count and titles

### 2. Fetch failed CI runs
- Call GitHub MCP tool for workflow runs or Actions
- Filter for `conclusion: failure` in last 24 hours
- Print workflow name, branch, and URL

### 3. Save sample output
- Write raw JSON to `logs/github_sample.json`
- Useful for debugging template rendering later

### 4. Add CLI command
```bash
python src/main.py fetch-github
```

---

## Done When

- `fetch-github` prints PR count and failed run count
- `logs/github_sample.json` contains real repo data
- Works with your actual GitHub repo

---

## Next Step

→ [Step 5 — Email MCP Connect](./step-05-email-mcp-connect.md)
