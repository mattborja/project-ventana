#!/usr/bin/env python3

import asyncio
import base64
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

# ---------------------------------------------------------------------------
# Configuration — set these in .vscode/mcp.json or as environment variables
# ---------------------------------------------------------------------------
GIT_REMOTE_URL = os.environ.get("GIT_REMOTE_URL", "")
API_VER = "7.1"
REPO_COORDS: dict | None = None


def parse_remote_url(remote_url: str) -> dict:
    parsed = urllib.parse.urlparse(remote_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("GIT_REMOTE_URL must be a valid absolute HTTPS URL")

    segments = [segment for segment in parsed.path.split("/") if segment]
    try:
        git_index = segments.index("_git")
    except ValueError as exc:
        raise ValueError("GIT_REMOTE_URL must include the Azure Repos pattern /{org}/{project}/_git/{repo}") from exc

    if git_index < 2 or git_index + 1 >= len(segments):
        raise ValueError("GIT_REMOTE_URL must include the Azure Repos pattern /{org}/{project}/_git/{repo}")

    org_path = "/".join(segments[: git_index - 1])
    return {
        "host": parsed.hostname,
        "org_url": f"{parsed.scheme}://{parsed.netloc}/{org_path}",
        "project": segments[git_index - 1],
        "repo": segments[git_index + 1].removesuffix(".git"),
    }


def repo_coords() -> dict:
    global REPO_COORDS
    if REPO_COORDS is None:
        REPO_COORDS = parse_remote_url(GIT_REMOTE_URL)
    return REPO_COORDS


def validate_config() -> None:
    missing = [k for k, v in {
        "GIT_REMOTE_URL": GIT_REMOTE_URL,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    repo_coords()


# ---------------------------------------------------------------------------
# Git credential helper — retrieves cached credential
# ---------------------------------------------------------------------------
def get_git_credential(host: str) -> str:
    result = subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol=https\nhost={host}\n\n",
        capture_output=True,
        text=True,
        timeout=15,
    )
    for line in result.stdout.splitlines():
        if line.startswith("password="):
            return line[len("password="):].strip()
    raise RuntimeError(
        f"Credential retrieval failed for {host}. "
        f"Ensure a git credential helper is configured.\n{result.stderr}"
    )


def auth_header() -> dict:
    token = get_git_credential(repo_coords()["host"])
    encoded = base64.b64encode(f":{token}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


# ---------------------------------------------------------------------------
# Git host REST helpers
# ---------------------------------------------------------------------------
def https_get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"Accept": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def repo_base() -> str:
    coords = repo_coords()
    return (
        f"{coords['org_url']}"
        f"/{urllib.parse.quote(coords['project'], safe='')}"
        f"/_apis/git/repositories/{urllib.parse.quote(coords['repo'], safe='')}"
    )


def list_path(scope_path: str = "/") -> list[dict]:
    params = urllib.parse.urlencode({
        "scopePath":      scope_path,
        "recursionLevel": "OneLevel",
        "api-version":    API_VER,
    })
    body = https_get(f"{repo_base()}/items?{params}", auth_header())
    data = json.loads(body)
    return [
        {"path": item["path"], "type": "folder" if item.get("isFolder") else "file"}
        for item in data.get("value", [])
        if item["path"] != scope_path
    ]


def read_path(path: str) -> str:
    params = urllib.parse.urlencode({"path": path, "api-version": API_VER})
    body = https_get(
        f"{repo_base()}/items?{params}",
        {**auth_header(), "Accept": "application/octet-stream"},
    )
    return body.decode("utf-8")


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
app = Server("ventana-kb")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="list",
            description=(
                "List the contents of a path in the knowledge base repository. "
                "Returns an array of {path, type} objects where type is 'file' or 'folder'. "
                "Always start by listing '/' to discover the root INDEX.md and domain structure."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository path to list (e.g. '/' or '/knowledge-base'). Defaults to root.",
                        "default": "/",
                    }
                },
            },
        ),
        Tool(
            name="read",
            description=(
                "Read the contents of a file in the knowledge base repository. "
                "Use this to retrieve INDEX.md, RULES.md, and any domain content files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository path of the file to read (e.g. '/INDEX.md' or '/knowledge-base/mcp/RULES.md').",
                    }
                },
                "required": ["path"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        if name == "list":
            items = list_path(arguments.get("path", "/"))
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(items, indent=2))])
        if name == "read":
            path = arguments.get("path")
            if not path:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text="Error: path argument is required")],
                )
            return CallToolResult(content=[TextContent(type="text", text=read_path(path))])
        raise ValueError(f"Unknown tool: {name}")
    except Exception as exc:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Error: {exc}")],
        )


async def main() -> None:
    validate_config()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
