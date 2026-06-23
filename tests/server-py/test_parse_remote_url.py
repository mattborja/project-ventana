# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Matt Borja
# See the repository root LICENSE file for the full license text.

"""Tests for parse_remote_url in server.py.

The mcp package is mocked so that the test suite can run without it being
installed — the functions under test have no runtime dependency on it.
"""
import os
import sys
import importlib
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Inject mock mcp modules before loading server.py so the top-level imports
# resolve without requiring the real package to be installed.
# ---------------------------------------------------------------------------
for _mod in ('mcp', 'mcp.server', 'mcp.server.stdio', 'mcp.types'):
    sys.modules[_mod] = MagicMock()

_SERVER_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '../../client/onboarding/workspace/.vscode/mcp/server.py',
))
_spec = importlib.util.spec_from_file_location('server_py', _SERVER_PATH)
_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_server)

parse_remote_url = _server.parse_remote_url


# ---------------------------------------------------------------------------
# Valid Azure DevOps URLs
# ---------------------------------------------------------------------------

class TestAzureDevOpsUrls(unittest.TestCase):

    def test_azure_devops_services_url(self):
        r = parse_remote_url('https://dev.azure.com/myorg/myproject/_git/myrepo')
        self.assertTrue(r['is_azure_remote'])
        self.assertFalse(r['is_github_remote'])
        self.assertEqual(r['repo'], 'myrepo')
        self.assertEqual(r['project'], 'myproject')
        self.assertEqual(r['org_url'], 'https://dev.azure.com/myorg')
        self.assertEqual(r['protocol'], 'https')
        self.assertEqual(r['host'], 'dev.azure.com')

    def test_azure_devops_url_strips_git_suffix(self):
        r = parse_remote_url('https://dev.azure.com/myorg/myproject/_git/myrepo.git')
        self.assertTrue(r['is_azure_remote'])
        self.assertEqual(r['repo'], 'myrepo')

    def test_azure_devops_server_on_premises(self):
        r = parse_remote_url('https://ado.company.com/myorg/myproject/_git/myrepo')
        self.assertTrue(r['is_azure_remote'])
        self.assertEqual(r['repo'], 'myrepo')
        self.assertEqual(r['project'], 'myproject')
        self.assertEqual(r['org_url'], 'https://ado.company.com/myorg')

    def test_azure_devops_server_with_collection_prefix(self):
        r = parse_remote_url('https://ado.company.com/tfs/myorg/myproject/_git/myrepo')
        self.assertTrue(r['is_azure_remote'])
        self.assertEqual(r['repo'], 'myrepo')
        self.assertEqual(r['project'], 'myproject')
        self.assertEqual(r['org_url'], 'https://ado.company.com/tfs/myorg')


# ---------------------------------------------------------------------------
# Valid non-Azure URLs
# ---------------------------------------------------------------------------

class TestNonAzureUrls(unittest.TestCase):

    def test_github_url(self):
        r = parse_remote_url('https://github.com/myorg/myrepo.git')
        self.assertFalse(r['is_azure_remote'])
        self.assertTrue(r['is_github_remote'])
        self.assertEqual(r['repo'], 'myrepo')
        self.assertEqual(r['namespace'], 'myorg')
        self.assertEqual(r['protocol'], 'https')
        self.assertEqual(r['host'], 'github.com')

    def test_generic_https_url(self):
        r = parse_remote_url('https://git.example.com/org/suborg/myrepo')
        self.assertFalse(r['is_azure_remote'])
        self.assertFalse(r['is_github_remote'])
        self.assertEqual(r['repo'], 'myrepo')
        self.assertEqual(r['namespace'], 'org/suborg')
        self.assertEqual(r['origin'], 'https://git.example.com')

    def test_userinfo_is_excluded_from_origin_fields(self):
        r = parse_remote_url('https://user@git.example.com:8443/org/myrepo.git')
        self.assertEqual(r['origin'], 'https://git.example.com:8443')
        self.assertEqual(r['org_url'], 'https://git.example.com:8443')

    def test_localhost_http_is_permitted(self):
        r = parse_remote_url('http://localhost:8787/org/myrepo')
        self.assertEqual(r['protocol'], 'http')
        self.assertEqual(r['repo'], 'myrepo')
        self.assertFalse(r['is_azure_remote'])

    def test_loopback_ipv4_http_is_permitted(self):
        r = parse_remote_url('http://127.0.0.1:8080/org/myrepo')
        self.assertEqual(r['protocol'], 'http')
        self.assertEqual(r['repo'], 'myrepo')


# ---------------------------------------------------------------------------
# Invalid URLs — must raise
# ---------------------------------------------------------------------------

class TestInvalidUrls(unittest.TestCase):

    def test_http_non_localhost_raises(self):
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            parse_remote_url('http://git.example.com/org/repo')

    def test_non_url_string_raises(self):
        with self.assertRaises(ValueError):
            parse_remote_url('not-a-url')

    def test_url_with_no_repository_path_raises(self):
        with self.assertRaisesRegex(ValueError, 'repository path'):
            parse_remote_url('https://git.example.com/')

    def test_empty_repo_name_after_stripping_git_raises(self):
        with self.assertRaisesRegex(ValueError, 'repository name'):
            parse_remote_url('https://git.example.com/org/.git')


if __name__ == '__main__':
    unittest.main()
