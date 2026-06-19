# Knowledge Base Index

This is the root index of the knowledge base. Read this file first on every new session before querying any domain.

## What This Knowledge Base Contains

This repository is the authoritative knowledge base for the Project Ventana agentic workflow framework, maintained by Matt Borja. It is accessed by LLM agents over HTTPS via the Model Context Protocol — no local clone is required.

## Root-Level Files

| File | Purpose |
|------|---------|
| `INDEX.md` | This file — read first |
| `RULES.md` | Global rules that govern all LLM agent interactions with this knowledge base |

## Knowledge Base Domains

| Domain | Path | Description |
|--------|------|-------------|
| Model Context Protocol | `/knowledge-base/mcp/` | Concepts, implementation modes, and patterns for MCP in agentic workflows |

## How to Navigate This Knowledge Base

1. Read `/RULES.md` immediately after this file.
2. Use `list("<domain-path>")` to explore a domain's contents.
3. Read the domain's `INDEX.md` before reading any content files within it.
4. If a subdomain exists, read its `INDEX.md` and `RULES.md` before proceeding into its content.
5. Apply domain-specific `RULES.md` in addition to (not instead of) the global rules.

## Adding New Domains

To extend this knowledge base, create a new directory under `/knowledge-base/`, populate it with `INDEX.md` and `RULES.md`, and add it to the domain table above.
