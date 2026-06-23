# Knowledge Base Index

Read this file first at the start of every new session before consulting any domain content.

## What This Knowledge Base Contains

Use this file as the root map for your team's knowledge base. Replace the placeholder sections below with a concise description of the repository's purpose, the subjects it covers, and the domain layout you want agents to follow.

## Root-Level Files

| File | Purpose |
|------|---------|
| `INDEX.md` | Root entry point for agents and human readers |
| `RULES.md` | Global rules that apply across the entire knowledge base |

## Knowledge Base Domains

Populate this table with your own domains after creating them.

| Domain | Path | Description |
|--------|------|-------------|
| _(replace with your first domain)_ | `/knowledge-base/<domain>/` | Briefly describe what the domain covers |

## How to Navigate This Knowledge Base

1. Read `/RULES.md` immediately after this file.
2. Use `ventana-list("<domain-path>")` to explore the relevant domain.
3. Read a domain's `INDEX.md` before relying on its content files.
4. If a subdomain has its own `INDEX.md` or `RULES.md`, read those before proceeding.
5. Apply domain-specific rules in addition to the global rules.

## Getting Started for Maintainers

1. Replace the placeholder text in this file with repository-specific guidance.
2. Create one or more directories under `/knowledge-base/` for your domains.
3. Add `INDEX.md` files where agents need navigation help.
4. Add `RULES.md` files only where a domain needs extra rules beyond the global defaults.
5. Update the domain table above whenever you add, remove, or reorganize a domain.
