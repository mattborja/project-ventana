#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Matt Borja
# See the repository root LICENSE file for the full license text.
#
# Project Ventana — Developer Onboarding (Linux / macOS)
set -euo pipefail

echo ""
echo "Project Ventana — Developer Onboarding"
echo "======================================="
echo ""

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
fail() { echo "ERROR: $1" >&2; exit 1; }

command -v node >/dev/null 2>&1 || fail "Node.js is required. Install from https://nodejs.org"
command -v npm  >/dev/null 2>&1 || fail "npm is required (bundled with Node.js)."
command -v git  >/dev/null 2>&1 || fail "Git is required. Install from https://git-scm.com"

NODE_MAJOR=$(node --version | sed 's/^v//' | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 18 ]; then
  fail "Node.js 18 or higher is required (found $(node --version)). Update at https://nodejs.org"
fi

echo "Prerequisites satisfied (Node.js $(node --version), Git $(git --version | awk '{print $3}'))."
echo ""

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$SCRIPT_DIR/workspace"
MCP_DIR="$WORKSPACE_DIR/.vscode/mcp"

echo "Installing npm dependencies..."
npm --prefix "$MCP_DIR" install
echo ""

# ---------------------------------------------------------------------------
# Knowledge base configuration
# ---------------------------------------------------------------------------
echo "Configure your knowledge base connection."
echo "This value will be written into .vscode/mcp.json in the onboarding template."
echo ""

read -rp "  Git remote URL (token: GIT_REMOTE_URL, e.g. https://git.example.com/your-org/your-repo.git): " REMOTE_URL

MCP_JSON="$WORKSPACE_DIR/.vscode/mcp.json"

REMOTE_PARTS=$(node --input-type=commonjs -e "const u = new URL(process.argv[1]); console.log(`${u.protocol.slice(0, -1)} ${u.hostname}`)" "$REMOTE_URL" 2>/dev/null || true)
if [ -z "$REMOTE_PARTS" ]; then
  fail "GIT_REMOTE_URL must be a valid absolute URL."
fi
read -r GIT_PROTOCOL GIT_HOST <<<"$REMOTE_PARTS"

node --input-type=commonjs - "$MCP_JSON" "$REMOTE_URL" <<'JSEOF'
const fs   = require('fs');
const file = process.argv[1];
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
for (const server of Object.values(data.servers)) {
  server.env.GIT_REMOTE_URL = process.argv[2];
}
fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
JSEOF

echo ""
echo ".vscode/mcp.json updated in onboarding template."

# ---------------------------------------------------------------------------
# Git credential helper — trigger initial authentication
# ---------------------------------------------------------------------------
echo ""
echo "Authenticating with $GIT_HOST..."
echo "A browser window or credential prompt may appear."
echo ""

printf 'protocol=%s\nhost=%s\n\n' "$GIT_PROTOCOL" "$GIT_HOST" | git credential fill > /dev/null || true

echo ""
echo "======================================="
echo "Onboarding complete."
echo ""
echo "Next steps:"
echo "  1. Copy the onboarding template contents into your project root."
echo "  2. Open the project in VS Code."
echo "  3. The ventana-kb MCP server will appear in the MCP panel."
echo "  4. Open a Copilot or Claude chat and ask a question — the agent"
echo "     will consult the knowledge base automatically."
echo ""
echo "Knowledge base token: GIT_REMOTE_URL=$REMOTE_URL"
echo ""
