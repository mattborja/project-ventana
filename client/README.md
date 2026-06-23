# Setting Up Developer Workstations (client/)

> **Notice to AI Agents:** This document is provided for human orientation and training purposes only. It describes the structure and intended use of this directory for human readers — deployers, developers, and session participants. This file is not part of the knowledge base, does not represent authoritative guidance for AI-assisted workflows, and should not be treated as operational instructions. If you are an AI agent navigating a deployed knowledge base repository, this file is not present there. Proceed to `/INDEX.md` for authoritative content.

---

## What This Directory Is

The `client/` directory contains everything needed to connect a **developer's workstation** to the shared knowledge base. This is a per-person setup — each developer runs the onboarding script once on their own machine. There is no shared infrastructure to configure here; the shared piece is the KB repository (see `server/README.md`).

When onboarding is complete, the developer's IDE will have a running MCP server that gives connected AI agents (Claude Code, GitHub Copilot, etc.) direct read access to the knowledge base over HTTPS, using credentials already stored in the developer's git credential helper.

---

## Prerequisites

Each developer needs the following before running onboarding:

| Requirement | Notes |
|-------------|-------|
| **Git** | Must be installed and configured with a credential helper (GCM, osxkeychain, etc.) that can authenticate to the KB repository host |
| **Node.js ≥ 18** _(if using the JS server)_ | Download from [nodejs.org](https://nodejs.org) |
| **Python ≥ 3.10** _(if using the Python server)_ | Download from [python.org](https://python.org) |
| **VS Code** | The MCP server registration in `mcp.json` targets VS Code's MCP panel |
| **KB connection details** | The host URL, project name, and repository name — provided by whoever deployed the shared knowledge base repository |

Only one of Node.js or Python is required depending on which MCP server variant the developer chooses to use.

---

## What Gets Installed

The onboarding script prepares a `workspace/` folder that is a **template for the developer's project root**. After onboarding, the developer copies the contents of this folder into the root of whichever project they want the AI agent to have access to the knowledge base in.

Here is what is in the workspace template and what each piece does:

| File (relative to workspace/) | What it does |
|-------------------------------|-------------|
| `.vscode/mcp.json` | Registers the ventana-kb MCP server with VS Code. Contains the `GIT_REMOTE_URL` value needed to reach the knowledge base. The onboarding script fills this in automatically. |
| `.vscode/mcp/server.js` | The Node.js MCP server. VS Code launches this as a background process when the workspace is opened. It authenticates to the KB repository via the git credential helper and exposes `list` and `read` tools to the AI agent. |
| `.vscode/mcp/server.py` | The Python equivalent of the above. Use one or the other — delete whichever you do not plan to use, or remove its entry from `mcp.json`. |
| `.vscode/mcp/package.json` | Declares the Node.js dependency (`@modelcontextprotocol/sdk`). The onboarding script runs `npm install` here automatically. |
| `.vscode/mcp/requirements.txt` | Declares the Python dependency (`mcp`). Install manually with `pip install -r .vscode/mcp/requirements.txt` if using the Python server. |
| `CLAUDE.md` | Workspace instructions for Claude Code. Tells the agent to consult the KB at the start of every session before responding. Automatically loaded by Claude Code when the workspace is opened. |
| `.github/copilot-instructions.md` | The same instructions for GitHub Copilot. Automatically loaded by Copilot when the workspace is opened. |

---

## Onboarding Steps

### Step 1 — Run the onboarding script

From the root of this project-ventana repository, run the script for your platform:

```bash
# Linux / macOS
bash client/onboarding/setup.sh

# Windows (PowerShell)
pwsh client\onboarding\setup.ps1
```

The script will:
1. Verify that Node.js ≥ 18 and Git are installed.
2. Install the Node.js MCP server dependency (`@modelcontextprotocol/sdk`) into `.vscode/mcp/node_modules/`.
3. Prompt you for the `GIT_REMOTE_URL` value of the knowledge base repository, then write it into `.vscode/mcp.json`.
4. Attempt an initial authentication to the Git host via `git credential fill` to pre-populate credentials. A browser window or credential prompt may appear.

### Step 2 — Choose your MCP server variant

The workspace ships with both a Node.js server (`server.js`) and a Python server (`server.py`). Choose one:

- **Node.js** — no additional steps after onboarding; dependencies were installed in Step 1.
- **Python** — install dependencies manually: `pip install -r client/onboarding/workspace/.vscode/mcp/requirements.txt`

Open `client/onboarding/workspace/.vscode/mcp.json` and delete the entry for the variant you are **not** using: delete `ventana-kb-py` if using Node.js, or delete `ventana-kb` if using Python. Having both active is harmless but unnecessary.

### Step 3 — Copy the workspace template into your project

Copy the contents of `client/onboarding/workspace/` into the root of the developer's project. Do not copy the `workspace/` folder itself — copy what is inside it:

```bash
# Example: copying into a project called "my-project"
cp -r client/onboarding/workspace/. /path/to/my-project/
```

On Windows:
```powershell
Copy-Item -Recurse -Force client\onboarding\workspace\* C:\path\to\my-project\
```

### Step 4 — Open the project in VS Code

Open the project folder in VS Code. VS Code will detect `.vscode/mcp.json` and register the ventana-kb MCP server. It will appear in the MCP servers panel (accessible via the GitHub Copilot icon or the VS Code MCP extension).

### Step 5 — Verify the connection

Open a Copilot or Claude Code chat in the project and ask a simple question that the KB would cover. The agent should call `list("/")` and `read("/INDEX.md")` before responding — you will see these tool calls in the chat if tool use is visible in your IDE configuration.

If the MCP server fails to start, check:
- The `GIT_REMOTE_URL` value in `.vscode/mcp.json` is correct.
- `git credential fill protocol=https host=YOUR_HOST` returns a password when run in a terminal.
- Node.js (or Python) is on the system PATH visible to VS Code.

---

## Repeating Onboarding for a New Project

The onboarding script only needs to be run once. After that, to enable KB access in additional projects, simply copy the `workspace/` template into each new project root — the Git host credentials and MCP server files are already in place.
