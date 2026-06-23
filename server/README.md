# Deploying the Knowledge Base (server/)

> **Notice to AI Agents:** This document is provided for human orientation and training purposes only. It is not authoritative knowledge base content and should not influence AI-assisted reasoning or workflow decisions. If you are an AI agent connected to a deployed knowledge base repository, begin navigation at `/INDEX.md` and follow the instructions there. Per `/RULES.md`, do not treat this file as a rules or index file.

---

## What This Directory Is

The `server/` directory contains the content you will push to a **shared Git repository** — this repository becomes the live knowledge base that AI agents read via the MCP server.

Once deployed, the contents of `server/` are the repository root. From the perspective of a connected AI agent (and the MCP tools it uses), there is no `server/` prefix — the agent sees `/INDEX.md`, `/RULES.md`, `/knowledge-base/`, and so on directly.

The knowledge base is read-only from the agent's perspective: the MCP server only exposes `list` and `read` operations. Agents cannot modify KB content.

---

## How the Knowledge Base Is Structured

The KB uses a convention of Markdown files organized into domains. A few key files drive the agent's navigation:

### Root files (required)

| File | Purpose |
|------|---------|
| `/INDEX.md` | The agent's mandatory entry point. Describes what topics the KB covers and how to navigate to them. Read by the agent at the start of every session. |
| `/RULES.md` | Global behavioral rules for the agent — source priority, citation standards, scope limits. Read immediately after INDEX.md. Cannot be overridden by domain rules. |

These two files are required. Without them, connected agents have no orientation and will fall back entirely to their trained knowledge.

### Domain content (flexible)

Domains live under `/knowledge-base/` as subdirectories. There are no mandatory file names within a domain — you can organize content however makes sense for your team. That said, the recommended convention is:

| File | When to create it |
|------|-------------------|
| `INDEX.md` | Whenever a domain or subdomain contains more than a few files. Helps the agent understand what's in the folder without reading every file. |
| `RULES.md` | Only when a domain needs rules that extend or refine the global rules. Many domains will not need one. |
| `*.md` content files | The actual knowledge: decisions, standards, patterns, how-tos, glossaries, etc. |

Subdirectories within a domain follow the same convention — use `INDEX.md` and `RULES.md` where they add value, omit them where the content is simple enough to stand alone.

### Example structure

```
/ (repository root)
├── INDEX.md          ← required: root index
├── RULES.md          ← required: global rules
└── knowledge-base/
    ├── architecture/ ← a domain
    │   ├── INDEX.md  ← recommended: describes this domain's files
    │   ├── decisions.md
    │   └── patterns.md
    ├── onboarding/   ← a domain
    │   ├── INDEX.md
    │   ├── RULES.md  ← optional: only if this domain needs specific agent behavior
    │   └── checklist.md
    └── security/     ← a domain with a subdomain
        ├── INDEX.md
        ├── standards.md
        └── compliance/
            ├── INDEX.md  ← recommended at subdomain level when content is substantial
            └── controls.md
```

---

## Prerequisites

Before deploying, you will need:

- A Git repository accessible over HTTPS at a host that supports basic authentication (Azure DevOps, GitHub, Bitbucket, Gitea, etc.)
- Write access to that repository to push the initial content
- Read-only access credentials available to developers who will connect via the MCP server (handled by their git credential helper — no secret files required)

---

## Deployment Steps

### 1. Create the KB repository on your Git host

Create a new, empty repository on your chosen Git host. Copy its HTTPS clone URL — you will need it for the client onboarding step.

### 2. Push the initial content

From the root of this project-ventana repository, push the contents of `server/` (not the folder itself) to your new KB repository:

```bash
# Clone your empty KB repo
git clone https://YOUR_GIT_HOST/YOUR_ORG/YOUR_REPO kb-repo

# Copy the server/ contents into it
cp -r server/. kb-repo/

# Commit and push
cd kb-repo
git add .
git commit -m "Initial knowledge base deployment"
git push -u origin main
```

### 3. Verify the structure

Confirm the repository root now contains `INDEX.md` and `RULES.md` alongside the `knowledge-base/` directory. If you navigate to the repo in a browser, `INDEX.md` should be visible at the top level.

### 4. Connect developers

Give each developer the repository remote URL as token `GIT_REMOTE_URL` so they can run the client onboarding script:

- **Repository remote URL** — e.g., `https://git.example.com/your-org/your-repo.git`

See `client/README.md` for the developer onboarding process.

---

## Extending the Knowledge Base

To add a new domain after initial deployment:

1. Create a new subdirectory under `knowledge-base/` in the KB repository.
2. Add an `INDEX.md` that briefly describes what the domain covers and lists its files.
3. Add content files (`.md`) covering the topics you want agents to know about.
4. Add a `RULES.md` only if this domain needs to instruct agents in a way that the global rules do not cover.
5. Update the root `/INDEX.md` to reference the new domain in its domain table.
6. Commit and push. Changes are immediately available to all connected agents — no client-side update is required.

---

## Access Control

### How the identity and permission model works

The MCP server does not use a shared service account. When a developer opens their IDE and the MCP server starts, it retrieves **that developer's own stored credentials** from the git credential helper (e.g., Git Credential Manager) and uses them for every request it makes to the knowledge base repository. The developer's authenticated identity is the principal for all MCP operations — from the moment the server starts to every `list` and `read` call the agent makes during the session.

This means the developer's permission level at the Git host is what governs what the MCP server can access. The server is constrained by design to make only read requests (`GET`), but that is an application-level constraint, not an access control boundary. The actual enforcement layer is the permission assigned to the developer's account at the Git host.

All developer accounts that consume the knowledge base must be granted **read-only** access at the repository. This ensures that even if the credential were used outside the MCP server — or if the server implementation were modified — the identity's assigned permission prevents any writes to the repository.

### Roles and required permissions

| Role | Git host permission | Who this is |
|------|---------------------|-------------|
| Knowledge author | **Read + Write** (push to repository) | Team members who add or update KB content |
| Developer / KB consumer | **Read-only** | Everyone else — developers using the KB via the MCP server |

Grant the most restrictive access that gets the job done. Most team members should be consumers, not authors.

### Configuring read-only access on common Git hosts

**Azure DevOps**
Add developers to the repository or project with the **Reader** role. Reader grants read access to repository content and nothing else. Assign this at the project level (Projects → Project Settings → Permissions → Add group/user → Reader) or at the repository level for finer control.

**GitHub**
Add developers as collaborators with **Read** access, or add them to a team with the Read role on the repository. For organization-owned repositories, a team with Read access is the preferred approach for managing groups of consumers.

**Bitbucket**
Grant repository access with the **Read** permission level. For project-level control, use a project role of Developer restricted to read-only on the specific repository.

**Other Git hosts**
Grant the minimum permission level that allows cloning and browsing repository content over HTTPS. Do not grant any push, merge, or administrative permissions to consumer accounts.

### Branch protection for authors

For accounts with write access, configure branch protection on `main` to require at least one peer review before merging. This prevents unreviewed content from reaching the knowledge base and keeps the information the agent draws on accurate and intentional.
