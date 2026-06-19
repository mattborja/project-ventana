# Project Ventana — Claude Code Instructions

This workspace is connected to a knowledge base repository via the **ventana-kb** MCP server.

## Knowledge Base Access

The MCP server exposes two tools:

- `list(path)` — lists the contents of a path in the knowledge base repository
- `read(path)` — reads the contents of a file from the knowledge base repository

## Required Workflow

Before answering any question or generating any output that depends on project-specific knowledge, you **must** consult the knowledge base in this order:

1. Call `list("/")` to retrieve the root structure.
2. Call `read("/INDEX.md")` to load the global index.
3. Call `read("/RULES.md")` to load the global rules. Follow them without exception.
4. Navigate to the relevant domain by calling `list("/<domain>")`, then read that domain's `INDEX.md` and `RULES.md`.
5. Repeat recursively into subdomains as needed until you have located the authoritative content for the request.

## Priority Order

When constructing any response, apply information in this priority order:

1. **Knowledge base** (via ventana-kb MCP tools) — authoritative
2. **Trained knowledge** — supplementary, only where the KB is silent
3. **Web / external sources** — last resort, only when explicitly requested

Never rely on trained knowledge or external sources for facts that the knowledge base is expected to cover. If you cannot find the answer in the KB, say so explicitly before falling back.

## Local Augmentation

If the developer has added local context files to this workspace outside the knowledge base, they will reference them in their prompt. Treat those files as supplementary authoritative context, consulted after the KB and before trained knowledge.
