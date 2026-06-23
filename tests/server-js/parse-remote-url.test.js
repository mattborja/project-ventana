import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseRemoteUrl } from '../../client/onboarding/workspace/.vscode/mcp/server.js';

// ---------------------------------------------------------------------------
// Valid Azure DevOps URLs
// ---------------------------------------------------------------------------

test('Azure DevOps Services URL is parsed correctly', () => {
  const r = parseRemoteUrl('https://dev.azure.com/myorg/myproject/_git/myrepo');
  assert.equal(r.isAzureRemote, true);
  assert.equal(r.isGitHubRemote, false);
  assert.equal(r.repo, 'myrepo');
  assert.equal(r.project, 'myproject');
  assert.equal(r.orgUrl, 'https://dev.azure.com/myorg');
  assert.equal(r.protocol, 'https');
  assert.equal(r.host, 'dev.azure.com');
});

test('Azure DevOps Services URL with .git suffix strips suffix from repo name', () => {
  const r = parseRemoteUrl('https://dev.azure.com/myorg/myproject/_git/myrepo.git');
  assert.equal(r.isAzureRemote, true);
  assert.equal(r.repo, 'myrepo');
});

test('Azure DevOps Server on-premises URL is parsed correctly', () => {
  const r = parseRemoteUrl('https://ado.company.com/myorg/myproject/_git/myrepo');
  assert.equal(r.isAzureRemote, true);
  assert.equal(r.repo, 'myrepo');
  assert.equal(r.project, 'myproject');
  assert.equal(r.orgUrl, 'https://ado.company.com/myorg');
});

test('Azure DevOps Server with collection prefix is parsed correctly', () => {
  const r = parseRemoteUrl('https://ado.company.com/tfs/myorg/myproject/_git/myrepo');
  assert.equal(r.isAzureRemote, true);
  assert.equal(r.repo, 'myrepo');
  assert.equal(r.project, 'myproject');
  assert.equal(r.orgUrl, 'https://ado.company.com/tfs/myorg');
});

// ---------------------------------------------------------------------------
// Valid non-Azure URLs
// ---------------------------------------------------------------------------

test('GitHub URL is parsed correctly', () => {
  const r = parseRemoteUrl('https://github.com/myorg/myrepo.git');
  assert.equal(r.isAzureRemote, false);
  assert.equal(r.isGitHubRemote, true);
  assert.equal(r.repo, 'myrepo');
  assert.equal(r.namespace, 'myorg');
  assert.equal(r.protocol, 'https');
  assert.equal(r.host, 'github.com');
});

test('Generic HTTPS Git URL is parsed correctly', () => {
  const r = parseRemoteUrl('https://git.example.com/org/suborg/myrepo');
  assert.equal(r.isAzureRemote, false);
  assert.equal(r.isGitHubRemote, false);
  assert.equal(r.repo, 'myrepo');
  assert.equal(r.namespace, 'org/suborg');
  assert.equal(r.origin, 'https://git.example.com');
});

test('Localhost HTTP URL is permitted', () => {
  const r = parseRemoteUrl('http://localhost:8787/org/myrepo');
  assert.equal(r.protocol, 'http');
  assert.equal(r.repo, 'myrepo');
  assert.equal(r.isAzureRemote, false);
});

test('127.0.0.1 HTTP URL is permitted', () => {
  const r = parseRemoteUrl('http://127.0.0.1:8080/org/myrepo');
  assert.equal(r.protocol, 'http');
  assert.equal(r.repo, 'myrepo');
});

// ---------------------------------------------------------------------------
// Invalid URLs — must throw
// ---------------------------------------------------------------------------

test('HTTP non-localhost URL throws', () => {
  assert.throws(
    () => parseRemoteUrl('http://git.example.com/org/repo'),
    /HTTPS/
  );
});

test('Non-URL string throws', () => {
  assert.throws(
    () => parseRemoteUrl('not-a-url'),
    /valid absolute URL/
  );
});

test('URL with no repository path throws', () => {
  assert.throws(
    () => parseRemoteUrl('https://git.example.com/'),
    /repository path/
  );
});

test('URL where repo name is empty after stripping .git throws', () => {
  assert.throws(
    () => parseRemoteUrl('https://git.example.com/org/.git'),
    /repository name/
  );
});
