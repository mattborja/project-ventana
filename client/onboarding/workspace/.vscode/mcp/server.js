#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execFileSync } from 'child_process';
import https from 'https';
import { URL } from 'url';

// ---------------------------------------------------------------------------
// Configuration — set these in .vscode/mcp.json or as environment variables
// ---------------------------------------------------------------------------
const ORG_URL  = (process.env.GIT_HOST_URL  ?? '').replace(/\/$/, '');
const PROJECT  =  process.env.GIT_PROJECT   ?? '';
const REPO     =  process.env.GIT_REPO      ?? '';
const API_VER  = '7.1';

function validateConfig() {
  const missing = Object.entries({ GIT_HOST_URL: ORG_URL, GIT_PROJECT: PROJECT, GIT_REPO: REPO })
    .filter(([, v]) => !v)
    .map(([k]) => k);
  if (missing.length) throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
}

// ---------------------------------------------------------------------------
// Git credential helper — retrieves cached credential
// ---------------------------------------------------------------------------
function getGcmCredential(host) {
  const input = `protocol=https\nhost=${host}\n\n`;
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
  const host = new URL(ORG_URL).hostname;
  const token = getGcmCredential(host);
  return { Authorization: `Basic ${Buffer.from(`:${token}`).toString('base64')}` };
}

// ---------------------------------------------------------------------------
// Git host REST helpers
// ---------------------------------------------------------------------------
function httpsGet(url, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const req = https.request(
      {
        hostname: parsed.hostname,
        path: parsed.pathname + parsed.search,
        method: 'GET',
        headers: { Accept: 'application/json', ...extraHeaders },
      },
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
  return `${ORG_URL}/${encodeURIComponent(PROJECT)}/_apis/git/repositories/${encodeURIComponent(REPO)}`;
}

// list — returns immediate children of a path
async function listPath(scopePath = '/') {
  const url = new URL(`${repoBase()}/items`);
  url.searchParams.set('scopePath', scopePath);
  url.searchParams.set('recursionLevel', 'OneLevel');
  url.searchParams.set('api-version', API_VER);

  const { body } = await httpsGet(url.toString(), authHeader());
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
  const url = new URL(`${repoBase()}/items`);
  url.searchParams.set('path', path);
  url.searchParams.set('api-version', API_VER);

  const { body } = await httpsGet(url.toString(), {
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
