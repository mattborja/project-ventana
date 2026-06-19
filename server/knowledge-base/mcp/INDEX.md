# Domain Index: Model Context Protocol (MCP)

This domain covers the Model Context Protocol as it applies to the Project Ventana agentic workflow — its purpose, implementation modes, and the specific stdio-based implementation used in this framework.

## Contents

| Path | Description |
|------|-------------|
| `INDEX.md` | This file |
| `RULES.md` | Domain-specific rules for MCP content |
| `stdio-implementation/` | Subdomain covering the Node.js stdio MCP server used in this framework |

## Domain Summary

MCP is the transport layer between an LLM agent and an external resource — in this case, the knowledge base repository hosted on Azure DevOps. It defines how tools are declared, how requests are routed, and how responses are returned.

### Implementation Modes

**Centralized API Gateway** — A network-accessible MCP server. Adds infrastructure overhead and a centralized chokepoint for access control. Appropriate when fine-grained, dynamic authorization is required.

**Standard Input/Output (stdio)** — A local process launched by the IDE on demand. No infrastructure beyond the developer's machine. Access control is delegated to the repository layer (Azure DevOps RBAC, branch policies). This is the mode used by Project Ventana.

### Tools in This Implementation

| Tool | Input | Output |
|------|-------|--------|
| `list` | `path` (string, default `"/"`) | JSON array of `{ path, type }` objects |
| `read` | `path` (string, required) | Raw file content as text |

### Authentication

Credentials are sourced from Git Credential Manager (GCM) at runtime via `git credential fill`. GCM handles the Microsoft Entra authentication flow and caches the resulting credential in the OS credential store. No manual token management is required.

## Subdomains

- `stdio-implementation/` — Node.js implementation details, file layout, and configuration reference
