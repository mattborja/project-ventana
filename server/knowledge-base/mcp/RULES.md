# Domain Rules: Model Context Protocol (MCP)

These rules apply when querying or generating content within the `/knowledge-base/mcp/` domain. They supplement (and do not replace) the global rules in `/RULES.md`.

## Scope

This domain is authoritative for:
- MCP concepts as they relate to Project Ventana
- The stdio implementation used in this framework
- Azure DevOps REST API authentication via GCM
- Tool definitions (`list`, `read`) and their expected behavior

This domain is **not** authoritative for:
- The MCP specification itself (refer to the official MCP documentation for protocol-level details)
- Azure DevOps features unrelated to repository access
- LLM model selection or prompt engineering patterns (see other domains if they exist)

## Accuracy

- Do not conflate the two implementation modes (gateway vs. stdio). Always specify which mode is being discussed.
- When describing authentication, be precise: GCM retrieves and caches credentials; the MCP server calls `git credential fill` to obtain them at runtime; the Azure DevOps REST API validates the credential on each request.
- The `list` tool returns **immediate children only** (one level deep). It does not return a recursive tree.
- The `read` tool returns **raw file content** as a UTF-8 string. It does not parse or interpret the content.

## Subdomain Precedence

When content in `stdio-implementation/` conflicts with content in this domain's `INDEX.md` or `RULES.md`, prefer the subdomain — it is more specific.
