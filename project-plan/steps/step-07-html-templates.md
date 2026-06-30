# Step 7 — HTML Email Templates

**Goal:** Make alert emails readable and professional using Jinja2.

**Estimated time:** 2 hours

---

## Tasks

### 1. Add dependency
```
jinja2
```
```bash
pip install jinja2
pip freeze > requirements.txt   # or manually add jinja2
```

### 2. Create `templates/ci_alert.html`
Include:
- Repo name
- Workflow name
- Branch
- Commit author
- Failure time
- Link button to GitHub Actions run

### 3. Create template renderer helper
- `src/template_renderer.py` or function in workflow file
- Load template, render with failure data dict

### 4. Update CI alert workflow
- Render HTML instead of plain text
- Keep `--dry-run` printing HTML preview

---

## Done When

- CI alert email renders as formatted HTML in inbox
- Dry-run prints HTML to terminal
- Template handles zero failures gracefully (no send)

---

## Next Step

→ [Step 8 — Daily Digest](./step-08-daily-digest.md)
