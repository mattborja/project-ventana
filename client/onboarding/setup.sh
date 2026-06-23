#!/usr/bin/env bash
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
echo "These values will be written into workspace/.vscode/mcp.json."
echo ""

read -rp "  Git remote URL (token: GIT_REMOTE_URL, e.g. https://git.example.com/your-org/your-repo.git): " REMOTE_URL

MCP_JSON="$WORKSPACE_DIR/.vscode/mcp.json"

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
echo "workspace/.vscode/mcp.json updated."

# ---------------------------------------------------------------------------
# Git credential helper — trigger initial authentication
# ---------------------------------------------------------------------------
GIT_HOST=$(node --input-type=commonjs -e "console.log(new URL(process.argv[1]).hostname)" "$REMOTE_URL" 2>/dev/null || true)
if [ -z "$GIT_HOST" ]; then
  fail "GIT_REMOTE_URL must be a valid absolute URL."
fi

echo ""
echo "Authenticating with $GIT_HOST..."
echo "A browser window or credential prompt may appear."
echo ""

printf 'protocol=https\nhost=%s\n\n' "$GIT_HOST" | git credential fill > /dev/null || true

echo ""
echo "======================================="
echo "Onboarding complete."
echo ""
echo "Next steps:"
echo "  1. Copy workspace/ contents into your project root."
echo "  2. Open the project in VS Code."
echo "  3. The ventana-kb MCP server will appear in the MCP panel."
echo "  4. Open a Copilot or Claude chat and ask a question — the agent"
echo "     will consult the knowledge base automatically."
echo ""
echo "Knowledge base token: GIT_REMOTE_URL=$REMOTE_URL"
echo ""
