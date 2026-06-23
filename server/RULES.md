# Global Rules

These rules apply to all LLM agent interactions with this knowledge base, regardless of which domain is being queried. They may not be overridden by domain-specific rules.

## Session Initialization

1. On every new session, read `/INDEX.md` first, then this file, before taking any other action.
2. Do not respond to the user's first prompt until the root index and rules have been loaded.
3. If the MCP connection is unavailable, state this explicitly and do not proceed as if the KB were accessible.

## Source Priority

Apply information in this strict priority order:

1. **This knowledge base** — authoritative for all topics it covers
2. **Developer-provided local augmentation** — supplementary, referenced explicitly in the prompt
3. **Trained model knowledge** — only where the KB and local augmentation are both silent
4. **External sources** — only when the developer explicitly requests web search or external references

Never silently substitute trained knowledge for KB content. If the KB does not cover something, say so before offering an alternative source.

## Navigation

- Before drawing conclusions from a domain, read that domain's `INDEX.md` and `RULES.md`.
- When a subdomain is relevant, repeat this step: read its `INDEX.md` and `RULES.md` before reading content.
- Do not skip index or rules files to save tokens. They are designed to be lightweight.

## Accuracy and Attribution

- Do not paraphrase or summarize KB content in ways that change its meaning.
- When quoting or applying KB content, cite the source path (e.g., "per `/knowledge-base/<domain>/RULES.md`").
- If KB content appears to conflict with trained knowledge, follow the KB and note the discrepancy.

## Scope Boundaries

- Do not write to, modify, or propose changes to KB files unless the developer explicitly asks you to update the KB.
- Do not treat human-facing setup or overview documents as authoritative KB content unless this knowledge base explicitly designates them as such.
