#Requires -Version 5.1
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Matt Borja
# See the repository root LICENSE file for the full license text.
#
<#
.SYNOPSIS
    Project Ventana — Developer Onboarding (Windows / PowerShell)
.DESCRIPTION
    Checks prerequisites, installs npm dependencies, configures .vscode\mcp.json
    with the knowledge base remote URL, and triggers git credential authentication.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "Project Ventana — Developer Onboarding" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
function Assert-Command($name, $installHint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "$name is required. $installHint"
    }
}

Assert-Command 'node' 'Install from https://nodejs.org'
Assert-Command 'npm'  'Bundled with Node.js — reinstall from https://nodejs.org'
Assert-Command 'git'  'Install from https://git-scm.com'

$nodeMajor = [int]((node --version).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 18) {
    throw "Node.js 18 or higher is required (found $(node --version)). Update at https://nodejs.org"
}

$nodeVer = node --version
$gitVer  = (git --version) -replace 'git version ', ''
Write-Host "Prerequisites satisfied (Node.js $nodeVer, Git $gitVer)." -ForegroundColor Green
Write-Host ""

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceDir = Join-Path $ScriptDir 'workspace'
$McpDir       = Join-Path $WorkspaceDir '.vscode\mcp'

Write-Host "Installing npm dependencies..."
npm --prefix $McpDir install
Write-Host ""

# ---------------------------------------------------------------------------
# Knowledge base configuration
# ---------------------------------------------------------------------------
Write-Host "Configure your knowledge base connection."
Write-Host "This value will be written into .vscode\mcp.json in the onboarding template."
Write-Host ""

$RemoteUrl = Read-Host "  Git remote URL (token: GIT_REMOTE_URL, e.g. https://git.example.com/your-org/your-repo.git)"

try {
    $RemoteUri = [uri]$RemoteUrl
    if (-not $RemoteUri.IsAbsoluteUri -or -not $RemoteUri.Host) {
        throw
    }
} catch {
    throw "GIT_REMOTE_URL must be a valid absolute URL."
}

$McpJsonPath = Join-Path $WorkspaceDir '.vscode\mcp.json'
$McpJson = Get-Content $McpJsonPath -Raw | ConvertFrom-Json
foreach ($server in $McpJson.servers.PSObject.Properties) {
    $server.Value.env.GIT_REMOTE_URL = $RemoteUrl
}
$McpJson | ConvertTo-Json -Depth 10 | Set-Content $McpJsonPath

Write-Host ""
Write-Host ".vscode\mcp.json updated in onboarding template." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Git credential helper — trigger initial authentication
# ---------------------------------------------------------------------------
$GitHost = $RemoteUri.Host
$GitProtocol = $RemoteUri.Scheme

Write-Host ""
Write-Host "Authenticating with $GitHost..."
Write-Host "A browser window or credential prompt may appear."
Write-Host ""

try {
    "protocol=$GitProtocol`nhost=$GitHost`n`n" | git credential fill 2>$null | Out-Null
} catch {
    Write-Warning "Credential pre-fetch failed — you will be prompted on first MCP connection."
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "Onboarding complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy the onboarding template contents into your project root."
Write-Host "  2. Open the project in VS Code."
Write-Host "  3. The ventana-kb MCP server will appear in the MCP panel."
Write-Host "  4. Open a Copilot or Claude chat and ask a question — the agent"
Write-Host "     will consult the knowledge base automatically."
Write-Host ""
Write-Host "Knowledge base token: GIT_REMOTE_URL=$RemoteUrl"
Write-Host ""
