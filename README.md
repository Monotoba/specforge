# SpecForge

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/Monotoba/specforge/workflows/CI/badge.svg)](https://github.com/Monotoba/specforge/actions/workflows/ci.yml)
[![Release](https://github.com/Monotoba/specforge/workflows/Release/badge.svg)](https://github.com/Monotoba/specforge/actions/workflows/release.yml)
[![CodeQL](https://github.com/Monotoba/specforge/workflows/CodeQL%20Security%20Scan/badge.svg)](https://github.com/Monotoba/specforge/actions/workflows/codeql.yml)

**Local-first requirements engineering and specification management
for software and hardware projects.**

SpecForge tracks every artifact of a project — ideas, requirements,
decisions, tasks, tests, and verification evidence — as plain Markdown
files in a git repository. It enforces traceability between them, runs
a release gate to confirm every requirement is verified before you ship,
and integrates with AI tools so Claude Code can read and write your
project during development.

```
                   ┌─ exploration ─┐
ideas ──► candidates ──► requirements ──► tasks ──► verified ──► release
                              │                         │
                         decisions               verifications
                         assumptions
                         constraints
```

---

## Why SpecForge?

Most teams track work in one tool (Linear, Jira, GitHub Issues) and
requirements in another (Confluence, Google Docs, Notion) — or
nowhere at all. Nothing connects. When something breaks in production,
reconstructing why a decision was made, what requirement it served, and
what test was supposed to catch the problem is an archaeological dig.

SpecForge solves this by treating every piece of project knowledge as a
first-class artifact with a permanent ID, a status, and typed links to
other artifacts. The result is a queryable, auditable, AI-readable
project graph stored in plain files that any tool — your editor, your
CI pipeline, Claude Code — can read.

See [docs/THEORY.md](docs/THEORY.md) for the requirements engineering
principles behind the design.

---

## Feature summary

| Feature | Description |
|---------|-------------|
| 12 artifact kinds | idea, candidate, requirement, decision, assumption, constraint, change_order, task, test, verification, reference, conversation |
| 7 lifecycle statuses | draft → proposed → approved → implemented → verified → rejected/archived |
| Full traceability | Typed link fields (implements, verified_by, depends_on, source, tags) |
| Release gate | `specforge check` exits 0/1: all requirements verified + no open tasks |
| AI drafting | Anthropic, OpenAI, Ollama — `specforge draft` generates artifact bodies |
| Webhooks | HTTP callbacks on artifact events with HMAC-SHA256 signing |
| Plugins | Local Python hooks called synchronously on every mutation |
| Templates | Per-kind Markdown starters with front-matter tag/status presets |
| Bulk operations | Batch update-status, archive, tag-add/remove with filters and dry-run |
| MCP server | 11 tools for Claude Code / MCP-compatible assistants |
| REST daemon | FastAPI local service for web UI and programmatic access |
| Desktop app | PySide6 native client |
| Web UI | Browser client with dark/light/system theme |
| Git integration | Per-command `--git` flag or `git_commit: true` config default |
| Traceability export | CSV and Markdown matrices |
| Acceptance report | Markdown document for sign-off and audit |
| Context pack | JSON project summary optimised for LLM consumption |
| Search | Full-text AND search across titles and bodies |

---

## Installation

```bash
# Clone and install in editable mode
git clone <repo> specforge
cd specforge
pip install -e .                     # core + CLI + daemon
pip install -e ".[desktop]"          # + PySide6 desktop app
pip install -e ".[dev]"              # + pytest, ruff, mypy, httpx

# Verify
specforge --help
specforge-daemon --help
```

---

## Quick start

### 1. Create a project

```bash
specforge init ./my-project --git --name "My Project"
```

This creates the full directory scaffold, initialises git, and writes
a commented `.specforge.yaml` configuration file.

### 2. Capture an idea

```bash
specforge add-idea ./my-project "Offline support" \
  "Users lose work when the network drops."
```

### 3. Promote to a requirement

```bash
specforge promote ./my-project IDEA-0001 requirement \
  --text "The application shall serve cached content when no network
  connection is available, with no data loss on reconnect."
```

### 4. Add a linked task

```bash
specforge add-task ./my-project "Build offline cache layer" \
  --text "Implement SQLite-backed cache for the last 50 items.
  Sync to server on reconnect with conflict detection." \
  --implements REQ-0001 --git
```

### 5. Mark implemented and verify

```bash
specforge update-status ./my-project TASK-0001 implemented
specforge add-test ./my-project "Offline read test" \
  --text "Disable network. Open app. Assert cache loads < 2s." \
  --req REQ-0001
specforge add-verification ./my-project "Offline cache — QA passed" \
  --text "QA on iOS 17 and Android 14. All scenarios passed." \
  --req REQ-0001 --test TEST-0001 --git
specforge update-status ./my-project REQ-0001 verified --git
```

### 6. Check the release gate

```bash
specforge check ./my-project    # PASS / FAIL
specforge report ./my-project   # acceptance report
```

---

## AI drafting

Configure a provider once:

```bash
specforge config ./my-project --set llm.provider=anthropic
# reads ANTHROPIC_API_KEY env var automatically
# or: --set llm.provider=ollama  (no API key needed, runs locally)
```

Draft any artifact from a plain-language prompt:

```bash
specforge draft ./my-project requirement \
  "Passwords must be at least 12 characters and contain a mix of types" \
  --title "Password complexity policy"
```

SpecForge calls the LLM, displays the generated body in a Rich panel,
and asks for confirmation before creating the artifact. If the remote
provider fails, it offers to retry with local Ollama.

---

## Web UI

```bash
specforge-daemon     # start on http://127.0.0.1:8765
# open http://127.0.0.1:8765/ui
```

The web UI supports dark, light, and system colour modes. Click
**? Help** for built-in documentation on every feature.

For development (auto-restart on source changes):

```bash
SPECFORGE_DEV=1 specforge-daemon
```

---

## Claude Code / MCP integration

```bash
specforge mcp-config /path/to/project    # print config snippet
```

Paste the printed `mcpServers` block into Claude Code `settings.json`.
Claude can then call all 11 SpecForge tools directly in conversation:
create artifacts, search, check status, promote, verify.

Available MCP tools: `create_artifact`, `promote_artifact`,
`update_status`, `get_artifact`, `list_artifacts`, `link_artifact`,
`unlink_artifact`, `search`, `get_status`, `context_pack`, `validate`.

---

## Architecture

```
specforge_core/         Core library (no HTTP, no UI)
  models.py               Artifact, ArtifactKind, ArtifactStatus
  project.py              Project filesystem operations, ID generation
  trace.py                SQLite trace index (full-text search, graph queries)
  validation.py           Link and status consistency checks
  search.py               Multi-term AND search
  export.py               CSV and Markdown traceability matrix
  report.py               Acceptance report generator
  contextpack.py          AI context pack builder
  status.py               Project health dashboard
  adapter.py              Tool-call dispatcher for AI agents
  config.py               .specforge.yaml loader/saver
  llm.py                  Multi-provider LLM client (Anthropic/OpenAI/Ollama)
  bulk.py                 Batch artifact operations
  templates.py            Artifact template loader
  webhooks.py             HTTP webhook dispatcher
  plugins.py              Local Python plugin loader

specforge_cli/          Command-line interface (Typer)
  main.py                 All CLI commands

specforge_daemon/       Local REST API (FastAPI + uvicorn)
  api.py                  All REST endpoints + help content serving
  main.py                 uvicorn entry point
  mcp_server.py           MCP stdio JSON-RPC server
  watcher.py              watchdog auto-rebuild on file changes

specforge_studio/       Desktop GUI (PySide6)
  main.py                 Main window, dialogs, help viewer

specforge_web/          Browser client
  index.html              Single-page app (no build step)
  help/                   13 Markdown help files
```

All state lives in the project directory. The daemon and studio are
thin clients that delegate all logic to `specforge_core`.

---

## Configuration

`.specforge.yaml` at the project root:

```yaml
project_name: "My Project"
git_commit: false           # auto-commit every write

llm:
  provider: anthropic       # anthropic | openai | ollama
  model: claude-sonnet-4-6  # blank = provider default
  api_key: ""               # blank = ANTHROPIC_API_KEY env var
  base_url: ""              # blank = provider default

webhooks:
  - url: https://hooks.slack.com/services/XXX
    events: [artifact.created, artifact.promoted]
    secret: "optional-hmac-secret"
```

```bash
specforge config ./proj                          # show config
specforge config ./proj --set git_commit=true    # update key
specforge config ./proj --set llm.provider=ollama  # nested key
```

---

## Documentation

| Document | Contents |
|----------|---------|
| [docs/THEORY.md](docs/THEORY.md) | Requirements engineering theory: the cost curve, V-model, traceability, release gates |
| [docs/PROCESS.md](docs/PROCESS.md) | Step-by-step methodology: explore, specify, implement, verify, release |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | Definitions of every core concept: artifacts, kinds, statuses, links |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, module boundaries, data flow |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Extending SpecForge: plugins, webhooks, MCP, contributing |
| [docs/tutorials/01_rest_api_spec.md](docs/tutorials/01_rest_api_spec.md) | Tutorial: specifying a REST API with AI drafting |
| [docs/tutorials/02_hardware_bringup.md](docs/tutorials/02_hardware_bringup.md) | Tutorial: hardware bring-up verification |
| [docs/tutorials/03_sprint_planning.md](docs/tutorials/03_sprint_planning.md) | Tutorial: agile sprint planning |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

Built-in help system: start the daemon, open the web UI, and click
**? Help** — or run `specforge --help` / `specforge <command> --help`.

---

## Running tests

```bash
pytest                    # 310 tests
pytest tests/test_llm.py  # specific module
pytest -q                 # quiet mode
```

---

## Full lifecycle demo

```bash
./scripts/create_demo_project.sh    # 22-step end-to-end demo
```

This runs a complete project lifecycle — init, ideas, requirements,
decisions, tasks, tests, verification, export — and leaves the
resulting project in `examples/demo_project/` for inspection.
