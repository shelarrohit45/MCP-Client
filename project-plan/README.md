# MCP Client — Project Plan

Step-by-step plan to build a **GitHub + Email MCP** automation client.

**No AWS required.** Build one step at a time — finish and test each step before moving on.

---

## Project Goal

A Python app that:
- Connects to **GitHub MCP** (repo, PRs, CI runs)
- Connects to **Email MCP** (send reports and alerts)
- Sends CI failure alerts and daily repo digests

---

## How to Use This Plan

1. Open [checklist.md](./checklist.md) to track progress
2. Complete steps in order: `step-00` → `step-11`
3. Each step file has: **Goal**, **Tasks**, **Done when**, **Commands**
4. Do not skip ahead until the current step passes its "Done when" criteria

---

## Steps Overview

| Step | File | Focus | Est. Time |
|------|------|--------|-----------|
| 0 | [step-00-prerequisites.md](./steps/step-00-prerequisites.md) | Accounts, tokens, tools | 1–2 hrs |
| 1 | [step-01-basic-project.md](./steps/step-01-basic-project.md) | Folder structure, venv, hello run | 1 hr |
| 2 | [step-02-config-system.md](./steps/step-02-config-system.md) | YAML + `.env` config | 1–2 hrs |
| 3 | [step-03-github-mcp-connect.md](./steps/step-03-github-mcp-connect.md) | Connect GitHub MCP, list tools | 2–3 hrs |
| 4 | [step-04-github-data-fetch.md](./steps/step-04-github-data-fetch.md) | Fetch PRs and CI runs | 2–3 hrs |
| 5 | [step-05-email-mcp-connect.md](./steps/step-05-email-mcp-connect.md) | Connect Email MCP, test send | 2–3 hrs |
| 6 | [step-06-ci-alert-workflow.md](./steps/step-06-ci-alert-workflow.md) | First end-to-end workflow | 3–4 hrs |
| 7 | [step-07-html-templates.md](./steps/step-07-html-templates.md) | Jinja2 email templates | 2 hrs |
| 8 | [step-08-daily-digest.md](./steps/step-08-daily-digest.md) | Daily repo summary email | 3–4 hrs |
| 9 | [step-09-logging-dedup.md](./steps/step-09-logging-dedup.md) | Logs + duplicate protection | 2–3 hrs |
| 10 | [step-10-scheduler-docs.md](./steps/step-10-scheduler-docs.md) | Automation + README | 2–3 hrs |
| 11 | [step-11-agent-openrouter-firebase.md](./steps/step-11-agent-openrouter-firebase.md) | OpenRouter agent + Firebase memory | 2–3 wks |

**Total estimate:** 3–4 weeks for steps 0–10; step 11 is optional and incremental.

---

## Target Folder Structure (End State)

```
mcp-client/
├── project-plan/          ← you are here
├── src/
│   ├── main.py
│   ├── config.py
│   ├── mcp_manager.py
│   └── workflows/
├── config/
│   └── config.yaml
├── templates/
├── logs/
├── tests/
├── requirements.txt
├── .env
└── README.md
```

---

## Current Step

**Start here:** [Step 0 — Prerequisites](./steps/step-00-prerequisites.md)
