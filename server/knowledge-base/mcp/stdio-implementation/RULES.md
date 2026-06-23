# Subdomain Rules: stdio MCP Implementation

These rules apply when querying or generating content within `/knowledge-base/mcp/stdio-implementation/`. They supplement the domain rules in `/knowledge-base/mcp/RULES.md` and the global rules in `/RULES.md`.

## Scope

This subdomain is authoritative for:
- The specific files shipped in this repository that constitute the MCP integration
- Configuration values, environment variable names, and their expected formats
- Runtime behavior of `server.js` and `server.py` as implemented

## Implementation Constraints

- The server uses **ESM** (`"type": "module"` in `package.json`). Do not generate CJS (`require()`) alternatives unless the developer explicitly requests a CJS port.
- Credential retrieval is done via `git credential fill` (synchronous child process). Do not suggest replacing this with PAT environment variables or other credential mechanisms unless the git credential helper is confirmed unavailable in the target environment.
- The server intentionally uses Node.js built-in `http`/`https` modules rather than a third-party HTTP client to minimize dependencies.

## Error Handling

- Tool errors are returned as `{ isError: true, content: [{ type: "text", text: "Error: ..." }] }` so the LLM receives a descriptive message rather than a protocol-level failure.
- Configuration errors (missing env vars) cause the process to exit at startup, before accepting any connections. This is intentional — fail fast.

## Security Notes

- The credential returned by the git credential helper is used as a Basic auth token (`username:token` base64-encoded). This is the correct format for authentication over HTTPS on most Git hosts including GitHub and Azure DevOps.
- The server operates under the authenticated identity of the individual developer — it does not use a shared service account. Every request made to the repository is made as that developer.
- The server only makes `GET` requests by design. However, this is an application-level constraint, not the access control boundary. The actual enforcement layer is the permission assigned to the developer's account at the Git host: consumer accounts must be granted read-only (Reader) access so the repository itself enforces the restriction regardless of how the credential is used.
- Environment variables in `.vscode/mcp.json` are visible to any process with read access to the workspace. Do not store secrets in that file; use the git credential helper for credential management as designed.
