// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Matt Borja
// See the repository root LICENSE file for the full license text.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { interpolateTemplate } from '../../client/onboarding/workspace/.vscode/mcp/server.js';

// ---------------------------------------------------------------------------
// Basic substitution
// ---------------------------------------------------------------------------

test('substitutes a single token', () => {
  assert.equal(
    interpolateTemplate('{repo}', { repo: 'myrepo' }),
    'myrepo'
  );
});

test('substitutes multiple tokens', () => {
  assert.equal(
    interpolateTemplate('{origin}/{namespace}/{repo}', {
      origin: 'https://git.example.com',
      namespace: 'myorg',
      repo: 'myrepo',
    }),
    'https://git.example.com/myorg/myrepo'
  );
});

test('substitutes the same token appearing more than once', () => {
  assert.equal(
    interpolateTemplate('{repo}/{repo}', { repo: 'myrepo' }),
    'myrepo/myrepo'
  );
});

// ---------------------------------------------------------------------------
// Path encoding — scopePath and path keys are percent-encoded with / preserved
// ---------------------------------------------------------------------------

test('scopePath with a simple path passes through unmodified', () => {
  assert.equal(
    interpolateTemplate('{scopePath}', { scopePath: '/knowledge-base/mcp/' }),
    '/knowledge-base/mcp/'
  );
});

test('scopePath with special characters encodes them but preserves slashes', () => {
  assert.equal(
    interpolateTemplate('{scopePath}', { scopePath: '/path with spaces/file' }),
    '/path%20with%20spaces/file'
  );
});

test('path key is also percent-encoded with slashes preserved', () => {
  assert.equal(
    interpolateTemplate('{path}', { path: '/domain/sub dir/file.md' }),
    '/domain/sub%20dir/file.md'
  );
});

test('non-path keys are NOT percent-encoded', () => {
  // origin contains ':' and '//' which must not be encoded
  assert.equal(
    interpolateTemplate('{origin}', { origin: 'https://git.example.com' }),
    'https://git.example.com'
  );
});

// ---------------------------------------------------------------------------
// Unknown token — must throw
// ---------------------------------------------------------------------------

test('unknown token throws an error', () => {
  assert.throws(
    () => interpolateTemplate('{unknownKey}', { repo: 'myrepo' }),
    /Unknown URL template token/
  );
});
