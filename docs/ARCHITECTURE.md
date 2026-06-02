# Architecture

## Overview

SpecForge is a layered system. The core library contains all domain
logic. The CLI, daemon, studio, and web client are thin shells that
translate user input into core library calls and format the results.

```
┌─────────────────────────────────────────────────────┐
│                    User interfaces                   │
│  specforge_cli  specforge_daemon  specforge_studio   │
│  (Typer CLI)    (FastAPI + uvicorn) (PySide6)        │
│                 specforge_web                        │
│                 (browser SPA)                        │
└──────────────────────────┬──────────────────────────┘
                           │  calls
┌──────────────────────────▼──────────────────────────┐
│                  specforge_core                      │
│  project.py   trace.py   models.py   config.py      │
│  search.py    export.py  report.py   contextpack.py │
│  validation.py status.py adapter.py  llm.py         │
│  bulk.py      templates.py webhooks.py plugins.py   │
└──────────────────────────┬──────────────────────────┘
                           │  reads/writes
┌──────────────────────────▼──────────────────────────┐
│                    Project directory                 │
│  <root>/                                            │
│    .specforge.yaml          configuration           │
│    .specforge/plugins/      Python plugins          │
│    .specforge/templates/    artifact templates      │
│    specification/           requirement artifacts   │
│    development/             task/test artifacts     │
│    exploration/             idea artifacts          │
│    trace/traceability.sqlite  query index           │
└─────────────────────────────────────────────────────┘
```

**Design principle**: canonical data lives in the Markdown files.
SQLite is a generated index — it can always be rebuilt from the files
with `specforge trace`. No information exists only in SQLite.

---

## specforge_core

The core library has no dependency on any HTTP framework, UI toolkit,
or external service (except the optional LLM API call in `llm.py`).
Every function is callable from tests without a daemon or browser.

### models.py
Defines the `Artifact` Pydantic model and the `ArtifactKind` and
`ArtifactStatus` enumerations. These are the fundamental data types
used throughout the system.

```python
class Artifact(BaseModel):
    id: str
    kind: ArtifactKind
    title: str
    status: ArtifactStatus
    body: str
    tags: list[str]
    implements: list[str]
    verified_by: list[str]
    depends_on: list[str]
    source: str | None
    created_at: datetime
    updated_at: datetime
    path: Path | None          # set after loading from disk
```

### project.py
The `Project` class is the main interface to a project directory. It
handles:
- **ID generation**: scans the artifact directory for the next
  sequential ID within a kind (e.g., `REQ-0004` after `REQ-0003`)
- **Artifact caching**: maintains an mtime-based cache to avoid
  re-reading files on every access
- **Mutation methods**: `create_artifact`, `promote_artifact`,
  `update_status`, `link_artifact`, `unlink_artifact`
- **Event dispatch**: each mutation fires webhooks (async, background
  thread) and plugins (sync, same thread) after writing

```python
class Project:
    root: Path
    _artifact_cache: list[Artifact]    # mtime-keyed cache
    _plugin_cache: list[ModuleType]    # loaded once per instance

    def create_artifact(kind, title, body, **links) -> Artifact
    def promote_artifact(id, target_kind, **links) -> Artifact
    def update_status(id, new_status) -> Artifact
    def link_artifact(id, **updates) -> Artifact
    def unlink_artifact(id, **removals) -> Artifact
    def get_artifact(id) -> Artifact
    def artifacts() -> list[Artifact]
```

### trace.py
Manages the SQLite trace index. The schema has four tables:

```sql
CREATE TABLE artifacts (id TEXT, kind TEXT, status TEXT, title TEXT, path TEXT);
CREATE TABLE links (src_id TEXT, field TEXT, tgt_id TEXT);
CREATE TABLE bodies (id TEXT, body TEXT);         -- for full-text search
CREATE TABLE tags (id TEXT, tag TEXT);
```

The index is rebuilt by scanning all `.md` files in the project. It
is used for search, graph queries, and export.

### validation.py
Checks the project for consistency errors:
- Links that reference non-existent artifact IDs
- Requirements with no implementing tasks
- Tasks linked to non-existent requirements
- Status contradictions

### search.py
Multi-term AND search over artifact titles and bodies. Each search
term must appear in either the title or body for an artifact to match.

### export.py
Generates the traceability matrix: for each requirement, list all
implementing tasks and all verification evidence. Outputs CSV and
Markdown.

### report.py
Generates the acceptance report: a structured Markdown document
listing every requirement with its status and linked verifications.

### status.py
Computes the project health dashboard: artifact counts by kind and
status, open tasks list, unverified requirements, release gate result.

### config.py
Loads and saves `.specforge.yaml`. The `ProjectConfig` Pydantic model
contains all configuration fields. `load_config` is tolerant of
missing files, extra keys, and malformed YAML.

### llm.py
Multi-provider LLM client. All three providers (Anthropic, OpenAI,
Ollama) are called via `urllib.request` — no external HTTP library
required. `complete_with_fallback` tries the primary provider and
offers the user an Ollama fallback on failure.

### bulk.py
Batch artifact operations. `bulk_update` filters the artifact list
by kind, status, and/or tags, then applies one action (update-status,
archive, tag-add, tag-remove) to all matching artifacts.

### templates.py
Loads artifact body templates from `.specforge/templates/<kind>.md`.
Parses optional YAML front matter for metadata presets.

### webhooks.py
HTTP webhook dispatcher. `fire_event` starts a daemon thread that
POSTs a JSON payload to all registered webhook URLs whose event filter
matches. HMAC-SHA256 signing is applied when a secret is configured.
Failures are logged to stderr; the calling thread never blocks.

### plugins.py
Local Python plugin loader. `load_plugins` imports all `.py` files in
`.specforge/plugins/` using `importlib`. `fire_plugin_event` calls the
`on_event` function in each loaded plugin. Exceptions are caught; the
calling thread never blocks on a broken plugin.

### adapter.py
Tool-call dispatcher for AI agent integration. `handle_tool_call`
accepts a `{"action": "...", ...}` dict and dispatches it to the
appropriate project method. Returns `{"ok": bool, "result": ...,
"error": ...}`. Used by the MCP server and the `/tool-call` REST
endpoint.

---

## specforge_cli

The CLI is built with Typer. Each command:
1. Instantiates a `Project`
2. Calls one or more `specforge_core` functions
3. Formats the result with Rich

The CLI never contains business logic — it only translates command-line
arguments into core library calls.

Key patterns:
- `_eg(project, flag)` returns `True` if `--git` was passed OR
  `git_commit: true` is in config
- All artifact creation commands call `project.create_artifact()`
- The `bulk`, `draft`, `webhook`, `plugin`, and `template` commands
  are single Typer commands with an `action` argument

---

## specforge_daemon

The daemon is a FastAPI application running under uvicorn. All
endpoints:
1. Call `active_project()` to get the current open project
2. Delegate to `specforge_core`
3. Return JSON

There is no persistent session state beyond `_active_project` (the
last project opened via `POST /projects/open`).

### watcher.py
Uses `watchdog` to monitor the project directory for `.md` file
changes. On change, rebuilds the SQLite trace index automatically.

### mcp_server.py
An MCP stdio server. Reads JSON-RPC 2.0 requests from stdin,
dispatches them to `adapter.handle_tool_call`, writes responses to
stdout. Stateless — opens the project at startup.

---

## Data flow: artifact creation

```
User:  specforge add-req ./proj "Export DXF" --text "..."
                │
                ▼
CLI:   project.create_artifact(ArtifactKind.REQUIREMENT, ...)
                │
                ▼
Core:  generate REQ-NNNN → write Markdown file → invalidate_cache()
                │
                ├──► webhooks: background thread → POST to URLs
                └──► plugins: sync call → on_event(event, artifact, project)
                │
                ▼
CLI:   prints "Created REQ-NNNN: Export DXF"
```

---

## File format

Artifact files are UTF-8 Markdown with YAML front matter. The YAML
front matter uses the exact field names from the `Artifact` Pydantic
model, so `read_artifact` is a direct YAML parse + Pydantic validation.

Datetime fields are ISO 8601 strings. List fields are YAML lists. The
`path` field is not persisted (set at load time from the file path).

---

## Safety rule

No artifact becomes authoritative unless explicitly promoted or
approved. Conversations and exploration notes do not automatically
become requirements. The lifecycle status is explicit at every stage.
