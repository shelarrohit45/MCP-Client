# MCP Client — Project Plan

Step-by-step plan to build a **GitHub + Email MCP** automation client with an optional **OpenRouter agent** and **Firebase** memory.

**Status: complete** (Steps 0–11 implemented). See [README.md](../README.md) for usage and [docs/](../docs/) for architecture, Firebase, and testing.

---

## Project goal

A Python app that:

- Connects to **GitHub MCP** (repo, PRs, CI runs)
- Connects to **Email MCP** (send reports and alerts)
- Sends CI failure alerts and daily repo digests
- Optionally provides a natural-language **agent** with Firestore memory

**No AWS required.** Runs locally on your machine.

---

## How to use this plan

1. Open [checklist.md](./checklist.md) for progress tracking
2. Steps were completed in order: `step-00` → `step-11`
3. Each step file has: **Goal**, **Tasks**, **Done when**, **Commands**

---

## Steps overview

| Step | File | Focus | Status |
|------|------|--------|--------|
| 0 | [step-00-prerequisites.md](./steps/step-00-prerequisites.md) | Accounts, tokens, tools | Done |
| 1 | [step-01-basic-project.md](./steps/step-01-basic-project.md) | Folder structure, venv | Done |
| 2 | [step-02-config-system.md](./steps/step-02-config-system.md) | YAML + `.env` | Done |
| 3 | [step-03-github-mcp-connect.md](./steps/step-03-github-mcp-connect.md) | GitHub MCP | Done |
| 4 | [step-04-github-data-fetch.md](./steps/step-04-github-data-fetch.md) | Fetch PRs and CI | Done |
| 5 | [step-05-email-mcp-connect.md](./steps/step-05-email-mcp-connect.md) | Email MCP | Done |
| 6 | [step-06-ci-alert-workflow.md](./steps/step-06-ci-alert-workflow.md) | CI alert workflow | Done |
| 7 | [step-07-html-templates.md](./steps/step-07-html-templates.md) | Jinja2 templates | Done |
| 8 | [step-08-daily-digest.md](./steps/step-08-daily-digest.md) | Daily digest | Done |
| 9 | [step-09-logging-dedup.md](./steps/step-09-logging-dedup.md) | Logs + dedup | Done |
| 10 | [step-10-scheduler-docs.md](./steps/step-10-scheduler-docs.md) | Scheduler + README | Done |
| 11 | [step-11-agent-openrouter-firebase.md](./steps/step-11-agent-openrouter-firebase.md) | Agent + Firebase | Done |

---

## Documentation map

| Document | Contents |
|----------|----------|
| [README.md](../README.md) | Overview, quick start, CLI, config |
| [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) | System design, patterns, data flows |
| [docs/FIREBASE.md](../docs/FIREBASE.md) | Firestore schema, setup, testing |
| [docs/TESTING.md](../docs/TESTING.md) | Local, CI, and smoke tests |
| [checklist.md](./checklist.md) | Build progress checklist |

---

## Verify the build

```bash
source venv/bin/activate
./scripts/run_all_tests.sh --unit
python scripts/test_step11.py
```

Live smoke test: see [docs/TESTING.md](../docs/TESTING.md).

Run automation:

```bash
python src/main.py run-scheduler
```
