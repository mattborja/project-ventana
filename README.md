# Project Ventana

A proven agentic workflow framework that connects LLM agents to a shared enterprise knowledge base via a lightweight, stdio-based Model Context Protocol server — requiring no additional infrastructure beyond a Git repository and a runtime (Node.js or Python) already present on each developer's machine.

> **Status: Development**
>
> Project Ventana has progressed through **Research** and is currently in **Development** as this rebuild and iteration continues toward **Release** readiness.

Presented by **[Matt Borja](https://linkedin.com/in/mattborja)** at **ACCTC 2026**, hosted by **Pima Community College**, week of June 22nd, 2026.

> **Enabling an AI-Powered Workforce to Achieve Maximum Productivity**
> 
> Demonstration of a proven, viable workflow that exploits the agentic capabilities of AI to accelerate teams in their research, development, and release of technical solutions at scale.

![GitHub Repository QR Code](qrcode-github.png)

> **📄 Conference Slides:** [`slides.pdf`](slides.pdf) — placeholder available now; final slides will be committed here once ready. To be notified when the finalized deck and future updates are published, **Watch this repository** on GitHub (click **Watch → All Activity** or **Releases Only** at the top of the repo page).

---

## Architecture

![Architecture Overview](architecture.svg)

---

## Repository Structure

This repository is a deployment template. It contains two self-contained components with distinct deployment targets:

| Directory | Deploy to | Purpose |
|-----------|-----------|---------|
| `server/` | A shared Git repository (GitHub, Azure Repos, etc.) | The knowledge base — curated content the LLM reads on every connection |
| `client/` | Each developer's local machine | Onboarding scripts and workspace templates that wire up the MCP connection |

Neither component depends on the other at the file-system level. `server/` is deployed once by a maintainer; `client/` is run once per developer machine.

---

## Part 1 — Deploying the Server (Knowledge Base)

### What Gets Deployed

The `server/` directory is a **clean starter template** for a dedicated knowledge base repository on your chosen host (GitHub, Azure Repos, Bitbucket, Gitea, etc.). It intentionally ships without framework-specific domain content so teams can populate it only with their own authoritative knowledge. When deployed, the initial contents are:

```
/INDEX.md                          ← Starter root index; replace placeholder content
/RULES.md                          ← Starter global rules; customize as needed
```

You then add your own domain folders under `/knowledge-base/` and update `/INDEX.md` to match. The LLM agent accesses this repository over HTTPS via the MCP tools `list` and `read`. It never clones the repository — every connection retrieves the latest committed state directly from the remote.

### Prerequisites

- A Git hosting account (GitHub, Azure DevOps, Bitbucket, etc.)
- Permission to create a new Git repository
- Intended consumers (developers) need at minimum **read-only** access to the repository
- Recommended: branch policy on `main` requiring pull requests with at least one approver, to enforce content review before changes go live

### Steps

1. On your Git host, create a new repository (e.g., `knowledge-base`).
2. Copy the **contents** of `server/` — not the `server/` folder itself — into the root of that new repository.
3. Replace the placeholder text in `INDEX.md` and `RULES.md`, then add your first domain under `/knowledge-base/`.
4. Commit and push to the `main` branch.
5. Configure repository permissions:
   - Knowledge base maintainers: **write** access
   - Consuming developers: **read-only** access (prevents unauthorized edits)
6. Configure branch policies on `main`:
   - Require a pull request for all changes
   - Add designated approvers or a reviewer group for content governance
7. Record the repository URL as `GIT_REMOTE_URL` (for example, `https://github.com/your-org/knowledge-base.git` or `https://dev.azure.com/your-org/your-project/_git/knowledge-base`). Developers will need this during client setup.

### Extending the Knowledge Base

The starter template intentionally includes **no preloaded framework domains**. To add a new domain of knowledge:

1. Create a directory at `/knowledge-base/{domain-name}/`
2. Add `INDEX.md` (describe what the domain contains) and `RULES.md` (rules specific to this domain) at the domain root
3. Add content files and subdomains as needed, each with their own `INDEX.md` and `RULES.md`
4. Update `/INDEX.md` to add the new domain to the domain table

This recursive index-and-rules pattern is the core organizing principle. It lets LLM agents navigate large knowledge bases efficiently without walking the full directory tree.

---

## Part 2 — Deploying the Client (Developer Workstation)

### What Gets Deployed

The `client/onboarding/workspace/` directory contains the files that a developer installs into their local project workspace:

| File | Install location | Purpose |
|------|-----------------|---------|
| `.vscode/mcp/server.js` | `.vscode/mcp/` | Node.js stdio MCP server; proxies KB requests over HTTPS |
| `.vscode/mcp/server.py` | `.vscode/mcp/` | Python stdio MCP server; equivalent alternative to server.js |
| `.vscode/mcp/package.json` | `.vscode/mcp/` | Declares the `@modelcontextprotocol/sdk` dependency |
| `.vscode/mcp/requirements.txt` | `.vscode/mcp/` | Declares the `mcp` Python dependency |
| `.vscode/mcp.json` | `.vscode/` | Registers the MCP server with VS Code |
| `CLAUDE.md` | Workspace root | Instructs Claude Code to consult the KB first |
| `.github/copilot-instructions.md` | `.github/` | Instructs GitHub Copilot to consult the KB first |

The MCP server authenticates against the Git host using credentials cached by the developer's git credential helper (Git Credential Manager, osxkeychain, libsecret, etc.). No tokens are stored in files; the credential helper transparently manages authentication.

### Prerequisites

Each developer's machine needs:

- **Node.js 18 or later** (for `server.js`) — [nodejs.org](https://nodejs.org), **or Python 3.10 or later** (for `server.py`) — [python.org](https://www.python.org)
- **Git** with **Git Credential Manager** — included with Git for Windows; install separately on macOS/Linux via `brew install git-credential-manager` or the [GCM releases page](https://github.com/git-ecosystem/git-credential-manager/releases)
- **VS Code** — or another IDE with MCP server support

### Steps

**Step 1 — Configure Git remote URL**

Open `client/onboarding/workspace/.vscode/mcp.json` and replace the placeholder values in the `env` block with the repository details from Part 1:

```json
"env": {
  "GIT_REMOTE_URL": "<GIT_REMOTE_URL>"
}
```

The onboarding script can also patch this file interactively if preferred.

**Step 2 — Run the onboarding script**

From the root of this repository:

- **macOS / Linux:**
  ```bash
  bash client/onboarding/setup.sh
  ```
- **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File client\onboarding\setup.ps1
  ```

The script will:
- Verify Git prerequisites and the appropriate runtime (Node.js/npm for `server.js`, or Python/pip for `server.py`)
- Run `npm install` inside `client/onboarding/workspace/.vscode/mcp/` (if using `server.js`) or `pip install -r requirements.txt` (if using `server.py`)
- Prompt for your Git remote URL and write it into `.vscode/mcp.json`
- Trigger an initial GCM authentication against your Git host (a browser window or OS credential prompt may appear)

**Step 3 — Copy workspace files into the developer's project**

Copy the contents of `client/onboarding/workspace/` into the root of the developer's project workspace (the folder they open in VS Code). For each developer and each project they work on, the following files need to be present:

```
.vscode/mcp.json
.vscode/mcp/server.js              ← Node.js MCP server
.vscode/mcp/server.py              ← Python MCP server (alternative)
.vscode/mcp/package.json
.vscode/mcp/requirements.txt
CLAUDE.md                          ← if using Claude Code
.github/copilot-instructions.md    ← if using GitHub Copilot
```

**Step 4 — Open VS Code**

Open the workspace folder in VS Code. The `ventana-kb` MCP server will appear in the MCP panel and start automatically when a Copilot or Claude chat is opened.

### Verification

In a Copilot or Claude chat window, ask:

> "What domains are available in the knowledge base?"

The agent should call `ventana-list("/")` and `ventana-read("/INDEX.md")` via the `ventana-kb` MCP tool and return a summary of the knowledge base contents.

If the agent responds without invoking the MCP tool, check that:
- `.vscode/mcp.json` is present in the workspace root
- The `ventana-kb` server shows as active (not errored) in the MCP panel
- The `GIT_REMOTE_URL` value in `mcp.json` matches the repository deployed in Part 1
- GCM has a cached credential for the configured Git host (`git credential fill` should return a password without prompting)

---

## Part 3 — Local Workspace Augmentation

Developers are not blocked by the current state of the shared knowledge base. Any context that is missing or specific to an individual's work can be added as local files in the workspace.

To use local augmentation:

1. Create a folder (e.g., `local-context/`) in the workspace and add any relevant files
2. Reference it in `CLAUDE.md` or `.github/copilot-instructions.md`:
   ```
   Additionally, consult the files in /local-context/ as a supplementary
   authoritative source, to be applied after the knowledge base and before
   trained knowledge.
   ```

If the local context becomes a persistent, recurring need, add a standing reference to it in the workspace instructions file. This makes the augmentation automatic without requiring a knowledge base pull request.

---

## Benefits

- **Speed** — Corpus searches that previously took hours complete in seconds via an agent operating at computer speed against a structured, indexed knowledge base.
- **Accuracy** — Models grounded in domain-specific, authoritative content produce output calibrated to the actual environment rather than trained approximations.
- **Automation depth** — Teams using this pattern direct their agents to write and run tests, connect to databases and web applications, perform end-to-end and parity tests, and check for regressions — all within a single session.
- **Infrastructure reach** — Permissions, sequenced deployment prerequisites, and artifact preparation can also be automated within this same agentic pipeline.
- **Low overhead** — No centralized MCP gateway to operate. The stdio server runs locally on each developer's machine; access control is enforced entirely at the Git host layer.

---

## License

MIT License — Copyright (c) Matt Borja
