#Requires -Version 5.1
<#
.SYNOPSIS
    Project Ventana — Developer Onboarding (Windows / PowerShell)
.DESCRIPTION
    Checks prerequisites, installs npm dependencies, configures workspace\.vscode\mcp.json
    with Git host coordinates, and triggers git credential authentication.
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
Write-Host "These values will be written into workspace\.vscode\mcp.json."
Write-Host ""

$HostUrl  = Read-Host "  Git host URL (token: GIT_HOST_URL, e.g. https://git.example.com/your-namespace)"
$Project  = Read-Host "  Project name"
$RepoName = Read-Host "  Repository name"

$McpJsonPath = Join-Path $WorkspaceDir '.vscode\mcp.json'
$McpJson = Get-Content $McpJsonPath -Raw | ConvertFrom-Json
foreach ($server in $McpJson.servers.PSObject.Properties) {
    $server.Value.env.GIT_HOST_URL = $HostUrl
    $server.Value.env.GIT_PROJECT  = $Project
    $server.Value.env.GIT_REPO     = $RepoName
}
$McpJson | ConvertTo-Json -Depth 10 | Set-Content $McpJsonPath

Write-Host ""
Write-Host "workspace\.vscode\mcp.json updated." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Git credential helper — trigger initial authentication
# ---------------------------------------------------------------------------
$GitHost = ($HostUrl -replace 'https://', '').Split('/')[0]

Write-Host ""
Write-Host "Authenticating with $GitHost..."
Write-Host "A browser window or credential prompt may appear."
Write-Host ""

try {
    "protocol=https`nhost=$GitHost`n`n" | git credential fill 2>$null | Out-Null
} catch {
    Write-Warning "Credential pre-fetch failed — you will be prompted on first MCP connection."
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "Onboarding complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy workspace\ contents into your project root."
Write-Host "  2. Open the project in VS Code."
Write-Host "  3. The ventana-kb MCP server will appear in the MCP panel."
Write-Host "  4. Open a Copilot or Claude chat and ask a question — the agent"
Write-Host "     will consult the knowledge base automatically."
Write-Host ""
Write-Host "Knowledge base tokens: GIT_HOST_URL=$HostUrl, GIT_PROJECT=$Project, GIT_REPO=$RepoName"
Write-Host "Knowledge base remote token: set GIT_REMOTE_URL to your host-specific repository URL"
Write-Host ""
