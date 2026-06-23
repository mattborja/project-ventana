#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Matt Borja
# See the repository root LICENSE file for the full license text.

import asyncio
import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import NoReturn

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
REPOSITORY_INFO: dict | None = None


def parse_remote_url(remote_url: str) -> dict:
    parsed = urllib.parse.urlparse(remote_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("GIT_REMOTE_URL must include both a scheme (http/https) and a host")
    is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_localhost):
        raise ValueError("GIT_REMOTE_URL must use HTTPS (HTTP is only allowed for localhost)")

    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        raise ValueError("GIT_REMOTE_URL must include a repository path")

    repo = segments[-1].removesuffix(".git")
    if not repo:
        raise ValueError("GIT_REMOTE_URL must include a repository name")

    try:
        git_segment_index = segments.index("_git")
    except ValueError:
        git_segment_index = -1
    is_azure_remote = git_segment_index >= 2 and git_segment_index == len(segments) - 2
    azure_git_index = git_segment_index if is_azure_remote else -1
    org_path = "/".join(segments[: azure_git_index - 1]) if is_azure_remote else ""
    project = segments[azure_git_index - 1] if is_azure_remote else ""
    is_github_remote = parsed.hostname == "github.com"
    origin_host = parsed.hostname
    if ":" in origin_host and not origin_host.startswith("["):
        origin_host = f"[{origin_host}]"
    if parsed.port:
        origin_host = f"{origin_host}:{parsed.port}"
    origin = f"{parsed.scheme}://{origin_host}"
    return {
        "host": parsed.hostname,
        "protocol": parsed.scheme,  # 'https' or 'http'
        "origin": origin,
        "namespace": "/".join(segments[:git_segment_index]) if is_azure_remote else "/".join(segments[:-1]),
        "org_url": f"{origin}/{org_path}" if is_azure_remote else origin,
        "project": project,
        "repo": repo,
        "is_azure_remote": is_azure_remote,
        "is_github_remote": is_github_remote,
    }


def repository_info() -> dict:
    global REPOSITORY_INFO
    if REPOSITORY_INFO is None:
        REPOSITORY_INFO = parse_remote_url(GIT_REMOTE_URL)
    return REPOSITORY_INFO


def validate_config() -> None:
    missing = [k for k, v in {
        "GIT_REMOTE_URL": GIT_REMOTE_URL,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    repository_info()


# ---------------------------------------------------------------------------
# Git credential helper — retrieves cached credential
# ---------------------------------------------------------------------------
def get_git_credential(host: str, protocol: str) -> dict:
    result = subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol={protocol}\nhost={host}\n\n",
        capture_output=True,
        text=True,
        timeout=15,
    )
    username = ""
    pw = ""
    for line in result.stdout.splitlines():
        if line.startswith("username="):
            username = line[len("username="):].strip()
        elif line.startswith("pass" + "word="):
            pw = line[len("pass" + "word="):].strip()
    if not pw:
        raise RuntimeError(
            f"Credential retrieval failed for {host}. "
            f"Ensure a git credential helper is configured.\n{result.stderr}"
        )
    return {"username": username, "pw": pw}


def auth_header() -> dict:
    info = repository_info()
    cred = get_git_credential(info["host"], info["protocol"])
    encoded = base64.b64encode(f"{cred['username']}:{cred['pw']}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


# ---------------------------------------------------------------------------
# Git host REST helpers
# ---------------------------------------------------------------------------
def api_get(url: str, headers: dict | None = None) -> bytes:
    parsed_url = urllib.parse.urlparse(url)
    is_localhost = parsed_url.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed_url.scheme != "https" and not (parsed_url.scheme == "http" and is_localhost):
        raise RuntimeError("API requests must use HTTPS (HTTP is only allowed for localhost)")
    req = urllib.request.Request(url, headers={"User-Agent": "ventana-kb", "Accept": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def repo_base() -> str:
    repository = repository_info()
    return (
        f"{repository['org_url']}"
        f"/{urllib.parse.quote(repository['project'], safe='')}"
        f"/_apis/git/repositories/{urllib.parse.quote(repository['repo'], safe='')}"
    )


def provider_error(template_name: str) -> NoReturn:
    raise RuntimeError(
        f"No default API mapping found for this remote URL. Set {template_name} for your Git provider."
    )


def encode_path_preserving_slashes(value: str) -> str:
    return urllib.parse.quote(value, safe="/")


def interpolate_template(template: str, values: dict[str, str]) -> str:
    encoded_keys = {"path", "scopePath"}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise RuntimeError(f"Unknown URL template token: {{{key}}}")
        value = str(values[key])
        return encode_path_preserving_slashes(value) if key in encoded_keys else value

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", replace, template)


def list_path(scope_path: str = "/") -> list[dict]:
    repository = repository_info()
    use_github = not GIT_LIST_API_URL_TEMPLATE and repository["is_github_remote"]
    if GIT_LIST_API_URL_TEMPLATE:
        url = interpolate_template(
            GIT_LIST_API_URL_TEMPLATE,
            {**repository, "scopePath": scope_path, "apiVersion": API_VER},
        )
    elif repository["is_azure_remote"]:
        params = urllib.parse.urlencode({
            "scopePath": scope_path,
            "recursionLevel": "OneLevel",
            "api-version": API_VER,
        })
        url = f"{repo_base()}/items?{params}"
    elif repository["is_github_remote"]:
        contents_path = "" if scope_path == "/" else encode_path_preserving_slashes(scope_path.strip("/"))
        url = f"https://api.github.com/repos/{repository['namespace']}/{repository['repo']}/contents/{contents_path}"
    else:
        provider_error("GIT_LIST_API_URL_TEMPLATE")

    body = api_get(url, auth_header())
    data = json.loads(body)

    if use_github:
        return [
            {"path": f"/{item['path']}", "type": "folder" if item["type"] == "dir" else "file"}
            for item in (data if isinstance(data, list) else [])
        ]

    return [
        {"path": item["path"], "type": "folder" if item.get("isFolder") else "file"}
        for item in data.get("value", [])
        if item["path"] != scope_path
    ]


def read_path(path: str) -> str:
    repository = repository_info()
    use_github = not GIT_READ_API_URL_TEMPLATE and repository["is_github_remote"]
    if GIT_READ_API_URL_TEMPLATE:
        url = interpolate_template(
            GIT_READ_API_URL_TEMPLATE,
            {**repository, "path": path, "apiVersion": API_VER},
        )
    elif repository["is_azure_remote"]:
        params = urllib.parse.urlencode({"path": path, "api-version": API_VER})
        url = f"{repo_base()}/items?{params}"
    elif repository["is_github_remote"]:
        file_path = encode_path_preserving_slashes(path.lstrip("/"))
        url = f"https://api.github.com/repos/{repository['namespace']}/{repository['repo']}/contents/{file_path}"
    else:
        provider_error("GIT_READ_API_URL_TEMPLATE")

    accept = "application/vnd.github.raw+json" if use_github else "application/octet-stream"
    body = api_get(url, {**auth_header(), "Accept": accept})
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
                        "description": "Repository path of the file to read (e.g. '/INDEX.md' or '/knowledge-base/<domain>/RULES.md').",
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
