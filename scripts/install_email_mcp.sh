#!/usr/bin/env bash
# Install the Email MCP server locally (avoids npx startup issues).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js 18+ first."
  exit 1
fi

npm install
echo "Installed: $ROOT/node_modules/.bin/email-mcp"
"$ROOT/node_modules/.bin/email-mcp" help | head -5
