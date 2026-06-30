# Step 1 — Basic Python Project

**Goal:** Create empty project structure and confirm Python runs.

**Estimated time:** 1 hour

---

## Tasks

### 1. Create folders
```
mcp-client/
├── src/
├── templates/
├── logs/
├── tests/
└── config/
```

### 2. Virtual environment
```bash
cd mcp-client
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
pip install --upgrade pip
```

### 3. Create `requirements.txt`
```
mcp
python-dotenv
pyyaml
```

```bash
pip install -r requirements.txt
```

### 4. Create `.gitignore`
```
venv/
.env
logs/
__pycache__/
*.pyc
.DS_Store
```

### 5. Create `src/main.py`
```python
def main():
    print("MCP client started")


if __name__ == "__main__":
    main()
```

### 6. Run
```bash
python src/main.py
```

---

## Done When

- `python src/main.py` prints `MCP client started`
- No import errors
- `venv/` is in `.gitignore`

---

## Next Step

→ [Step 2 — Config System](./step-02-config-system.md)
