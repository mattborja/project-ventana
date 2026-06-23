# Tests

Unit tests for the pure logic layers of the Project Ventana MCP server implementations.

Tests cover the two functions shared by both variants — URL parsing and URL template interpolation — since these are the components most likely to behave differently across environments and Git providers.

---

## Structure

```
tests/
├── server-js/
│   ├── parse-remote-url.test.js       ← parseRemoteUrl (server.js)
│   └── interpolate-template.test.js   ← interpolateTemplate (server.js)
└── server-py/
    ├── test_parse_remote_url.py        ← parse_remote_url (server.py)
    └── test_interpolate_template.py    ← interpolate_template (server.py)
```

---

## Running the Tests

### Node.js (`server-js/`)

**Prerequisite:** Install the MCP server npm dependencies once:

```bash
cd client/onboarding/workspace/.vscode/mcp
npm install
cd -
```

**Run all JS tests** from the repository root:

```bash
node --test tests/server-js/*.test.js
```

**Run a single file:**

```bash
node --test tests/server-js/parse-remote-url.test.js
```

Requires Node.js ≥ 18 (the built-in `node:test` runner ships with Node 18+).

---

### Python (`server-py/`)

**No extra packages required** — the test files mock the `mcp` package automatically, so the test suite runs with the Python standard library only.

**Run all Python tests** from the repository root:

```bash
python3 -m unittest discover -s tests/server-py -p 'test_*.py'
```

**Run a single file:**

```bash
python3 -m unittest tests/server-py/test_parse_remote_url.py
```

Requires Python ≥ 3.10 (matches the production server requirement).

---

## CI Integration

Add these steps to your workflow after checking out the repository:

```yaml
- name: Install Node.js MCP server dependencies
  run: npm --prefix client/onboarding/workspace/.vscode/mcp install

- name: Run Node.js tests
  run: node --test tests/server-js/*.test.js

- name: Run Python tests
  run: python3 -m unittest discover -s tests/server-py -p 'test_*.py'
```
