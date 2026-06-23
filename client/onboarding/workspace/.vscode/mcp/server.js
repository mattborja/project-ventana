#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execFileSync } from 'child_process';
import http from 'http';
import https from 'https';
import { URL } from 'url';

// ---------------------------------------------------------------------------
// Configuration — set these in .vscode/mcp.json or as environment variables
// ---------------------------------------------------------------------------
const GIT_REMOTE_URL = process.env.GIT_REMOTE_URL ?? '';
const API_VER = '7.1';
const GIT_LIST_API_URL_TEMPLATE = process.env.GIT_LIST_API_URL_TEMPLATE ?? '';
const GIT_READ_API_URL_TEMPLATE = process.env.GIT_READ_API_URL_TEMPLATE ?? '';

function parseRemoteUrl(remoteUrl) {
  let parsed;
  try {
    parsed = new URL(remoteUrl);
  } catch {
    throw new Error('GIT_REMOTE_URL must be a valid absolute URL (e.g. https://git.example.com/org/repo.git)');
  }
  const isLocalhost = ['localhost', '127.0.0.1', '::1'].includes(parsed.hostname);
  if (parsed.protocol !== 'https:' && !(parsed.protocol === 'http:' && isLocalhost)) {
    throw new Error('GIT_REMOTE_URL must use HTTPS (HTTP is only allowed for localhost)');
  }

  const segments = parsed.pathname.split('/').filter(Boolean);
  if (!segments.length) {
    throw new Error('GIT_REMOTE_URL must include a repository path');
  }

  const repo = segments.at(-1).replace(/\.git$/, '');
  if (!repo) {
    throw new Error('GIT_REMOTE_URL must include a repository name');
  }

  const gitIndex = segments.lastIndexOf('_git');
  const isAzureRemote = gitIndex >= 2 && gitIndex + 1 === segments.length - 1;
  const orgPath = isAzureRemote ? segments.slice(0, gitIndex - 1).join('/') : '';
  const project = isAzureRemote ? segments[gitIndex - 1] : '';

  return {
    host: parsed.hostname,
    protocol: parsed.protocol.slice(0, -1),  // 'https' or 'http'
    origin: parsed.origin,
    namespace: segments.slice(0, -1).join('/'),
    orgUrl: `${parsed.origin}/${orgPath}`,
    project,
    repo,
    isAzureRemote,
  };
}

let repositoryInfoCache = null;

function repositoryInfo() {
  if (!repositoryInfoCache) repositoryInfoCache = parseRemoteUrl(GIT_REMOTE_URL);
  return repositoryInfoCache;
}

function validateConfig() {
  const missing = Object.entries({ GIT_REMOTE_URL })
    .filter(([, v]) => !v)
    .map(([k]) => k);
  if (missing.length) throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  repositoryInfo();
}

// ---------------------------------------------------------------------------
// Git credential helper — retrieves cached credential
// ---------------------------------------------------------------------------
function getGcmCredential(host, protocol) {
  const input = `protocol=${protocol}\nhost=${host}\n\n`;
  try {
    const out = execFileSync('git', ['credential', 'fill'], {
      input,
      encoding: 'utf8',
      timeout: 15_000,
    });
    const password = out.split('\n').find(l => l.startsWith('password='))?.slice('password='.length).trim();
    if (!password) throw new Error('No password returned by git credential helper');
    return password;
  } catch (err) {
    throw new Error(`Credential retrieval failed for ${host}: ${err.message}`);
  }
}

function authHeader() {
  const { host, protocol } = repositoryInfo();
  const token = getGcmCredential(host, protocol);
  return { Authorization: `Basic ${Buffer.from(`:${token}`).toString('base64')}` };
}

// ---------------------------------------------------------------------------
// Git host REST helpers
// ---------------------------------------------------------------------------
function apiGet(url, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const transport = parsed.protocol === 'https:' ? https : http;
    const options = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: { Accept: 'application/json', ...extraHeaders },
    };
    if (parsed.port) options.port = parseInt(parsed.port, 10);
    const req = transport.request(
      options,
      (res) => {
        const chunks = [];
        res.on('data', c => chunks.push(c));
        res.on('end', () => {
          const body = Buffer.concat(chunks).toString('utf8');
          if (res.statusCode >= 400) reject(new Error(`HTTP ${res.statusCode}: ${body}`));
          else resolve({ status: res.statusCode, body, contentType: res.headers['content-type'] ?? '' });
        });
      }
    );
    req.on('error', reject);
    req.end();
  });
}

function repoBase() {
  const { orgUrl, project, repo } = repositoryInfo();
  return `${orgUrl}/${encodeURIComponent(project)}/_apis/git/repositories/${encodeURIComponent(repo)}`;
}

function providerError(templateName) {
  throw new Error(
    `No default API mapping found for this remote URL. Set ${templateName} for your Git provider.`
  );
}

function interpolateTemplate(template, values) {
  const encodedKeys = new Set(['path', 'scopePath']);
  return template.replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (_match, key) => {
    if (!(key in values)) {
      throw new Error(`Unknown URL template token: {${key}}`);
    }
    const value = `${values[key]}`;
    return encodedKeys.has(key) ? encodeURIComponent(value).replace(/%2F/g, '/') : value;
  });
}

// list — returns immediate children of a path
async function listPath(scopePath = '/') {
  const repository = repositoryInfo();
  let url;
  if (GIT_LIST_API_URL_TEMPLATE) {
    url = interpolateTemplate(GIT_LIST_API_URL_TEMPLATE, { ...repository, scopePath, apiVersion: API_VER });
  } else if (repository.isAzureRemote) {
    const azureUrl = new URL(`${repoBase()}/items`);
    azureUrl.searchParams.set('scopePath', scopePath);
    azureUrl.searchParams.set('recursionLevel', 'OneLevel');
    azureUrl.searchParams.set('api-version', API_VER);
    url = azureUrl.toString();
  } else {
    providerError('GIT_LIST_API_URL_TEMPLATE');
  }

  const { body } = await apiGet(url, authHeader());
  const data = JSON.parse(body);

  return (data.value ?? [])
    .filter(item => item.path !== scopePath)
    .map(item => ({
      path:   item.path,
      type:   item.isFolder ? 'folder' : 'file',
      commit: item.commitId ?? null,
    }));
}

// read — returns raw file content
async function readPath(path) {
  const repository = repositoryInfo();
  let url;
  if (GIT_READ_API_URL_TEMPLATE) {
    url = interpolateTemplate(GIT_READ_API_URL_TEMPLATE, { ...repository, path, apiVersion: API_VER });
  } else if (repository.isAzureRemote) {
    const azureUrl = new URL(`${repoBase()}/items`);
    azureUrl.searchParams.set('path', path);
    azureUrl.searchParams.set('api-version', API_VER);
    url = azureUrl.toString();
  } else {
    providerError('GIT_READ_API_URL_TEMPLATE');
  }

  const { body } = await apiGet(url, {
    ...authHeader(),
    Accept: 'application/octet-stream',
  });
  return body;
}

// ---------------------------------------------------------------------------
// MCP server
// ---------------------------------------------------------------------------
const server = new Server(
  { name: 'ventana-kb', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'list',
      description:
        'List the contents of a path in the knowledge base repository. ' +
        'Returns an array of { path, type } objects where type is "file" or "folder". ' +
        'Always start by listing "/" to discover the root INDEX.md and domain structure.',
      inputSchema: {
        type: 'object',
        properties: {
          path: {
            type: 'string',
            description: 'Repository path to list (e.g. "/" or "/domain-a"). Defaults to root.',
            default: '/',
          },
        },
      },
    },
    {
      name: 'read',
      description:
        'Read the contents of a file in the knowledge base repository. ' +
        'Use this to retrieve INDEX.md, RULES.md, and any domain content files.',
      inputSchema: {
        type: 'object',
        properties: {
          path: {
            type: 'string',
            description: 'Repository path of the file to read (e.g. "/INDEX.md" or "/domain-a/RULES.md").',
          },
        },
        required: ['path'],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === 'list') {
      const items = await listPath(args?.path ?? '/');
      return { content: [{ type: 'text', text: JSON.stringify(items, null, 2) }] };
    }

    if (name === 'read') {
      if (!args?.path) return {
        isError: true,
        content: [{ type: 'text', text: 'Error: path argument is required' }],
      };
      const content = await readPath(args.path);
      return { content: [{ type: 'text', text: content }] };
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (err) {
    return {
      isError: true,
      content: [{ type: 'text', text: `Error: ${err.message}` }],
    };
  }
});

validateConfig();
const transport = new StdioServerTransport();
await server.connect(transport);
