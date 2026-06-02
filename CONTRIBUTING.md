# Contributing to SpecForge

Thank you for your interest in contributing. This document covers how
to set up a development environment, run tests, and submit changes.

---

## Development setup

```bash
git clone https://github.com/Monotoba/specforge.git
cd specforge
pip install -e ".[dev]" --break-system-packages
```

Run the test suite:

```bash
pytest
```

Run the daemon with auto-reload during development:

```bash
SPECFORGE_DEV=1 specforge-daemon
```

---

## Core principles

- **Canonical data lives in Markdown files.** SQLite is a generated
  index — never store information only in the database.
- **`specforge_core` must stay free of HTTP and UI dependencies.**
  All business logic lives there; the CLI, daemon, and studio are
  thin shells.
- **Every behaviour change needs a test.** The test suite runs on
  every pull request.
- **Small, focused commits with clear messages.** One logical change
  per commit.

---

## Running checks before submitting

```bash
pytest                                          # all tests must pass
ruff check specforge_core specforge_cli specforge_daemon   # no lint errors
```

---

## Adding a new feature

1. Create a branch: `git checkout -b feature/my-feature`
2. Write tests first (or alongside the implementation)
3. Implement the feature
4. Update `CHANGELOG.md` under the next version heading
5. Open a pull request against `main`

---

## Reporting bugs

Open an issue at https://github.com/Monotoba/specforge/issues with:
- Python version and OS
- The command that failed
- Full error output
- What you expected to happen

---

## Architecture notes

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system
design, and [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for
extension patterns (plugins, webhooks, MCP tools, new artifact kinds).
