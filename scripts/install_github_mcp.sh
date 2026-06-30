#!/usr/bin/env bash
# Download the official GitHub MCP server binary (macOS arm64).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$ROOT/bin"
VERSION="v1.5.0"
ARCH="$(uname -m)"

case "$ARCH" in
  arm64) ASSET="github-mcp-server_Darwin_arm64.tar.gz" ;;
  x86_64) ASSET="github-mcp-server_Darwin_x86_64.tar.gz" ;;
  *)
    echo "Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

URL="https://github.com/github/github-mcp-server/releases/download/${VERSION}/${ASSET}"
TMP_ARCHIVE="$(mktemp -t github-mcp-server.XXXXXX.tar.gz)"

mkdir -p "$BIN_DIR"
echo "Downloading $URL"
curl -fsSL "$URL" -o "$TMP_ARCHIVE"
tar -xzf "$TMP_ARCHIVE" -C "$BIN_DIR"
chmod +x "$BIN_DIR/github-mcp-server"
rm -f "$TMP_ARCHIVE"

echo "Installed: $BIN_DIR/github-mcp-server"
"$BIN_DIR/github-mcp-server" --version 2>/dev/null || echo "Binary ready."
