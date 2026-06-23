"""Tests for interpolate_template in server.py.

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
    sys.modules.setdefault(_mod, MagicMock())

_SERVER_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '../../client/onboarding/workspace/.vscode/mcp/server.py',
))
_spec = importlib.util.spec_from_file_location('server_py_tmpl', _SERVER_PATH)
_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_server)

interpolate_template = _server.interpolate_template


# ---------------------------------------------------------------------------
# Basic substitution
# ---------------------------------------------------------------------------

class TestBasicSubstitution(unittest.TestCase):

    def test_single_token(self):
        self.assertEqual(
            interpolate_template('{repo}', {'repo': 'myrepo'}),
            'myrepo',
        )

    def test_multiple_tokens(self):
        self.assertEqual(
            interpolate_template('{origin}/{namespace}/{repo}', {
                'origin': 'https://git.example.com',
                'namespace': 'myorg',
                'repo': 'myrepo',
            }),
            'https://git.example.com/myorg/myrepo',
        )

    def test_repeated_token(self):
        self.assertEqual(
            interpolate_template('{repo}/{repo}', {'repo': 'myrepo'}),
            'myrepo/myrepo',
        )


# ---------------------------------------------------------------------------
# Path encoding — scopePath and path keys are percent-encoded, slashes preserved
# ---------------------------------------------------------------------------

class TestPathEncoding(unittest.TestCase):

    def test_scope_path_simple_passes_through(self):
        self.assertEqual(
            interpolate_template('{scopePath}', {'scopePath': '/knowledge-base/mcp/'}),
            '/knowledge-base/mcp/',
        )

    def test_scope_path_encodes_special_chars_preserves_slashes(self):
        self.assertEqual(
            interpolate_template('{scopePath}', {'scopePath': '/path with spaces/file'}),
            '/path%20with%20spaces/file',
        )

    def test_path_key_encodes_special_chars_preserves_slashes(self):
        self.assertEqual(
            interpolate_template('{path}', {'path': '/domain/sub dir/file.md'}),
            '/domain/sub%20dir/file.md',
        )

    def test_non_path_key_not_encoded(self):
        # origin contains ':' and '//' which must not be encoded
        self.assertEqual(
            interpolate_template('{origin}', {'origin': 'https://git.example.com'}),
            'https://git.example.com',
        )


# ---------------------------------------------------------------------------
# Unknown token — must raise
# ---------------------------------------------------------------------------

class TestUnknownToken(unittest.TestCase):

    def test_unknown_token_raises(self):
        with self.assertRaisesRegex(RuntimeError, 'Unknown URL template token'):
            interpolate_template('{unknownKey}', {'repo': 'myrepo'})


if __name__ == '__main__':
    unittest.main()
