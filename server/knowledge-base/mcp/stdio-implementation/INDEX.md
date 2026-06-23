# Subdomain Index: stdio MCP Implementation

This subdomain documents the stdio MCP server shipped with Project Ventana — available in both Node.js and Python — its files, configuration, and runtime behavior.

## File Layout

These files live under `client/onboarding/workspace/` in this repository. The onboarding script (`client/onboarding/setup.sh` / `setup.ps1`) installs dependencies and patches the configuration in place. Developers then copy the contents of `workspace/` into their own project root.

| File | Purpose |
|------|---------|
| `client/onboarding/workspace/.vscode/mcp/server.js` | Node.js MCP server entry point. Launched by VS Code via `mcp.json`. |
| `client/onboarding/workspace/.vscode/mcp/server.py` | Python MCP server entry point. Launched by VS Code via `mcp.json`. |
| `client/onboarding/workspace/.vscode/mcp/package.json` | Declares the `@modelcontextprotocol/sdk` dependency and sets `"type": "module"` for ESM. |
| `client/onboarding/workspace/.vscode/mcp/requirements.txt` | Declares the `mcp` dependency for the Python variant. |
| `client/onboarding/workspace/.vscode/mcp.json` | Registers both server variants with VS Code. Edit the `env` block to supply `GIT_REMOTE_URL`, then remove the entry you are not using. |
| `client/onboarding/workspace/CLAUDE.md` | Workspace instructions for Claude Code — directs the agent to consult the KB first. |
| `client/onboarding/workspace/.github/copilot-instructions.md` | Equivalent instructions for GitHub Copilot. |

## Configuration

The server is configured entirely through environment variables, supplied via `.vscode/mcp.json`. Both variants use the same variable names:

| Variable | Description | Example |
|----------|-------------|---------|
| `GIT_REMOTE_URL` | HTTPS remote URL of the knowledge base repository | `https://git.example.com/your-org/knowledge-base.git` |
| `GIT_LIST_API_URL_TEMPLATE` *(optional)* | List endpoint template for non-default Git host APIs. Supported template tokens: `{origin}`, `{host}`, `{namespace}`, `{repo}`, `{scopePath}`, `{apiVersion}`. | `https://api.example.com/repos/{namespace}/{repo}/tree?path={scopePath}` |
| `GIT_READ_API_URL_TEMPLATE` *(optional)* | Read endpoint template for non-default Git host APIs. Supported template tokens: `{origin}`, `{host}`, `{namespace}`, `{repo}`, `{path}`, `{apiVersion}`. | `https://api.example.com/repos/{namespace}/{repo}/raw?path={path}` |

The server validates `GIT_REMOTE_URL` at startup and exits with a descriptive error if it is missing or malformed.

## Runtime Flow

1. VS Code launches the MCP server as a child process when the `ventana-kb` server is activated.
2. The server calls `git credential fill` with the Git host to retrieve the cached credential from the configured credential helper.
3. The credential is encoded as HTTP Basic auth (`username:token` base64-encoded) and attached to every REST request.
4. Tool calls from the LLM agent are dispatched to `list` or `read`, which call the Git host Items API over HTTPS and return the result as text content.

## Git Host REST Endpoints Used

The server auto-detects the Git provider from the remote URL and uses the appropriate REST API:

### GitHub (auto-detected for `github.com` remotes)

| Operation | Endpoint |
|-----------|----------|
| List path | `GET https://api.github.com/repos/{owner}/{repo}/contents/{path}` |
| Read file | `GET https://api.github.com/repos/{owner}/{repo}/contents/{path}` with `Accept: application/vnd.github.raw+json` |

### Azure Repos (auto-detected for URLs containing `/_git/`)

| Operation | Endpoint |
|-----------|----------|
| List path | `GET /{org}/{project}/_apis/git/repositories/{repo}/items?scopePath={path}&recursionLevel=OneLevel&api-version=7.1` |
| Read file | `GET /{org}/{project}/_apis/git/repositories/{repo}/items?path={path}&api-version=7.1` with `Accept: application/octet-stream` |

### Other providers

For Git hosts that are not auto-detected, supply `GIT_LIST_API_URL_TEMPLATE` and `GIT_READ_API_URL_TEMPLATE` to map `list` and `read` requests to your provider-specific REST endpoints.

## Dependencies

**Node.js variant**
- Node.js ≥ 18 — required for top-level `await`
- `@modelcontextprotocol/sdk` ≥ 1.0.0 — handles MCP protocol framing over stdio

**Python variant**
- Python ≥ 3.10 — required for `dict | None` union type syntax
- `mcp` ≥ 1.0.0 — handles MCP protocol framing over stdio; install with `pip install -r requirements.txt`

**Both variants**
- Git + a configured git credential helper — required for credential retrieval; no additional auth setup needed after initial sign-in
