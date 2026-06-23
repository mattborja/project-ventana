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
GIT_LIST_API_URL_TEMPLATE = os.environ.get("GIT_LIST_API_URL_TEMPLATE", "")
GIT_READ_API_URL_TEMPLATE = os.environ.get("GIT_READ_API_URL_TEMPLATE", "")
REPO_COORDS: dict | None = None


def parse_remote_url(remote_url: str) -> dict:
    parsed = urllib.parse.urlparse(remote_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("GIT_REMOTE_URL must be a valid HTTPS remote URL")
    if parsed.scheme != "https":
        raise ValueError("GIT_REMOTE_URL must use HTTPS")

    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        raise ValueError("GIT_REMOTE_URL must include a repository path")

    repo = segments[-1].removesuffix(".git")
    if not repo:
        raise ValueError("GIT_REMOTE_URL must include a repository name")

    git_index = len(segments) - 2 if len(segments) >= 2 and segments[-2] == "_git" else -1
    is_azure_remote = git_index >= 1
    org_path = "/".join(segments[: git_index - 1]) if is_azure_remote else ""
    project = segments[git_index - 1] if is_azure_remote else ""
    return {
        "host": parsed.hostname,
        "origin": f"{parsed.scheme}://{parsed.netloc}",
        "namespace": "/".join(segments[:-1]),
        "org_url": f"{parsed.scheme}://{parsed.netloc}/{org_path}",
        "project": project,
        "repo": repo,
        "is_azure_remote": is_azure_remote,
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


def provider_error(template_name: str) -> None:
    raise RuntimeError(
        f"No default API mapping found for this remote URL. Set {template_name} for your Git provider."
    )


def interpolate_template(template: str, values: dict[str, str]) -> str:
    def replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key not in values:
            raise RuntimeError(f"Unknown URL template token: {{{key}}}")
        return str(values[key])

    import re

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", replace, template)


def list_path(scope_path: str = "/") -> list[dict]:
    coords = repo_coords()
    if GIT_LIST_API_URL_TEMPLATE:
        url = interpolate_template(
            GIT_LIST_API_URL_TEMPLATE,
            {**coords, "scopePath": scope_path, "apiVersion": API_VER},
        )
    elif coords["is_azure_remote"]:
        params = urllib.parse.urlencode({
            "scopePath": scope_path,
            "recursionLevel": "OneLevel",
            "api-version": API_VER,
        })
        url = f"{repo_base()}/items?{params}"
    else:
        provider_error("GIT_LIST_API_URL_TEMPLATE")

    body = https_get(url, auth_header())
    data = json.loads(body)
    return [
        {"path": item["path"], "type": "folder" if item.get("isFolder") else "file"}
        for item in data.get("value", [])
        if item["path"] != scope_path
    ]


def read_path(path: str) -> str:
    coords = repo_coords()
    if GIT_READ_API_URL_TEMPLATE:
        url = interpolate_template(
            GIT_READ_API_URL_TEMPLATE,
            {**coords, "path": path, "apiVersion": API_VER},
        )
    elif coords["is_azure_remote"]:
        params = urllib.parse.urlencode({"path": path, "api-version": API_VER})
        url = f"{repo_base()}/items?{params}"
    else:
        provider_error("GIT_READ_API_URL_TEMPLATE")

    body = https_get(url, {**auth_header(), "Accept": "application/octet-stream"})
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
