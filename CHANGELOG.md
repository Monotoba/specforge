# Changelog

## 0.21.0

- MCP server expanded from 11 to 15 tools (version bumped to 0.20.0 in server info):
  - `check_gate` — release gate check (pass bool + open tasks + unverified requirements)
  - `draft_artifact` — AI-generate artifact body from prompt, create immediately (no confirm in MCP mode)
  - `bulk_update` — batch update-status/archive/tag-add/tag-remove with kind/status/tag filters and dry_run
  - `list_templates` — list available templates with kind, preset tags, and body preview
- Daemon: `POST /draft` REST endpoint — AI drafting over HTTP; accepts `{kind, prompt, title?, tags?, git_commit?}`; returns created artifact JSON; HTTP 502 on LLM error, 400 on unknown kind
- Tests: 320 (was 310); 10 new tests covering all 4 new MCP tools and the /draft endpoint

## 0.20.0

- Bulk operations: `specforge bulk <path> <action> [--kind K] [--status S] [--tag T] [--to S2] [--add-tag] [--remove-tag] [--dry-run]`
  - Actions: `update-status`, `archive`, `tag-add`, `tag-remove`
  - Filters: kind, current status, tag (all must match if multiple `--tag` flags)
  - `--dry-run` shows affected artifacts without writing
- `specforge_core/bulk.py`: `bulk_update(project, action, filters, params, dry_run)` pure function
- Tutorial articles in `docs/tutorials/`:
  1. `01_rest_api_spec.md` — REST API spec with AI drafting, traceability, and release gate
  2. `02_hardware_bringup.md` — Hardware bring-up with constraints, bench verification, sign-off report
  3. `03_sprint_planning.md` — Agile sprint: bulk task creation, AI drafting, webhooks, context pack
- Tests: 310 (was 295); 15 new bulk tests covering all 4 actions, filters, dry-run, and CLI.

## 0.19.0

- Artifact templates: `.specforge/templates/<kind>.md` — optional YAML front matter (tags, etc.) + Markdown body stub.
- `specforge template list <path>` — shows available templates.
- `specforge template new <path> <kind> [--title] [--no-confirm] [--tag]` — creates artifact pre-filled from template; merges template tags.
- `specforge template edit <path> <kind>` — opens template in `$EDITOR`; creates file if missing.
- `project.init()` writes built-in templates for `requirement`, `task`, and `test` (idempotent — never overwrites existing).
- Tests: 295 (was 277); 18 new template tests covering load, list, init scaffold, CLI round-trips.

## 0.18.0

- Multi-model support is now complete: Anthropic, OpenAI-compatible, and Ollama providers all wired.
- `specforge config --set llm.provider=ollama` (and `llm.model`, `llm.api_key`, `llm.base_url`) — dotted-key support for nested config fields.
- Ollama fallback prompt fires on any remote LLM failure; user can confirm or decline.
- No code changes from 0.17.0 beyond the dotted-key config extension.

## 0.17.0

- AI-assisted drafting: `specforge draft <path> <kind> <prompt> [--title] [--no-confirm] [--git] [--tag]` — calls an LLM to generate artifact body, shows it in a Rich panel, prompts to confirm before creating.
- Multi-provider LLM client (`specforge_core/llm.py`): Anthropic, OpenAI-compatible, and Ollama — all via stdlib `urllib.request`, zero new runtime dependencies.
- `LLMConfig` in `ProjectConfig` — configure provider, model, api_key, base_url in `.specforge.yaml`. API keys fall back to `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` env vars.
- Ollama fallback: when a remote provider fails, prompts "Use local Ollama instead?" and retries if confirmed.
- `specforge config --set llm.provider=ollama` — dotted-key support for nested config fields.
- Tests: 277 (was 249); 28 new tests covering LLM config, all three providers, fallback logic, and draft CLI.

## 0.16.0

- Plugin system: drop a `*.py` file in `.specforge/plugins/` to activate it. Define `on_event(event, artifact, project)` to receive artifact lifecycle events (created, promoted, status_changed, linked, unlinked). Plugins run synchronously after each mutation; exceptions are caught and logged to stderr, the mutation still completes.
- `specforge plugin list <path>` — lists discovered `.py` files with `on_event` presence status.
- `project.init()` creates `.specforge/plugins/` and writes `example_plugin.py.disabled` showing the interface.
- No config entry needed — file-based discovery only.
- Tests: 249 (was 230); 19 new plugin tests covering discovery, dispatch, error handling, all 5 event types, CLI, and cache reuse.

## 0.15.0

- Webhook system: `WebhookEntry` Pydantic model in `.specforge.yaml`; `fire_event()` dispatches JSON POSTs to registered URLs on artifact events (created, promoted, status_changed, linked, unlinked) in background threads. HMAC-SHA256 signing with optional secret. Event filtering via empty event list = subscribe to all. Failures logged to stderr, never block.
- Mutation methods (create_artifact, promote_artifact, update_status, link_artifact, unlink_artifact) all fire webhooks via fire_event() calls.
- CLI: `specforge webhook add/list/remove/test` — manage webhook subscriptions; `test` fires a synthetic ping event to verify connectivity.
- Daemon: `GET /webhooks` (list), `POST /webhooks` (add), `DELETE /webhooks?url=...` (remove).
- Tests: 230 (was 210); comprehensive webhook test suite covering dispatch, HMAC signing, event filtering, CLI round-trips, daemon endpoints, and integration with artifact lifecycle.

## 0.14.0

- `specforge show` link resolution: linked artifact IDs now display as `ID  [kind/status]`; missing links marked as `[missing]`. Enables one-stop reading of artifact context without multiple lookups.
- `scripts/create_demo_project.sh` comprehensive overhaul: now exercises config (`--name`, `--set git_commit`), tags (`--tag`), link resolution (via show), status dashboard, CI gate check (`specforge check`), and search by tag. 22 steps covering the full feature set.
- No new test additions (210 passing); `show` link resolution has no observable externals that need testing.

## 0.13.0

- `specforge edit <path> <id>` — open artifact in `$VISUAL`/`$EDITOR`; invalidates cache after save; warns on YAML parse errors; exits 1 if no editor set or editor exits non-zero.
- README: fully updated to 0.13.0 — config section, link/unlink commands, 11-tool MCP table, all new commands.
- Tests: 210 (was 204).

## 0.12.0

- `.specforge.yaml` config file: `project_name` (used in report titles and status dashboard) and `git_commit` (default for all write commands). Missing file returns safe defaults.
- `Project.config` — lazy-loaded property; `Project.reload_config()` for explicit refresh.
- `_eg(project, flag)` helper — all 16 write commands now honour `git_commit` from config; `--git` flag still overrides.
- `specforge config <path> [--set key=value]` — show config or update a single key.
- `specforge init --name <name>` — set project name at creation time.
- `specforge init` always writes a commented default `.specforge.yaml`.
- `project_name` wired into acceptance report title and status dashboard rule.
- Tests: 204 (was 185).

## 0.11.0

- `Project.unlink_artifact(id, **removals, clear_source)` — removes specific values from list link fields; `clear_source=True` nulls the source field.
- `specforge unlink <path> <id> [--implements] [--req] [--test] [--depends-on] [--tag] [--source] [--git]` — complement to `specforge link`.
- Daemon: `POST /artifacts/{id}/unlink` with `UnlinkArtifactRequest`.
- AI adapter: `unlink_artifact` action.
- MCP: `unlink_artifact` tool (11 tools total).
- `Project._next_id(kind)` — derives the next artifact ID from the cached artifact list instead of a second `rglob` scan; falls back to filesystem scan only on empty projects.
- Tests: 185 (was 172).

## 0.10.0

- `Project.link_artifact(id, **updates)` — append links to an existing artifact; list fields merged without duplicates; `source` replaced.
- `specforge link <path> <id> [--implements] [--req] [--test] [--depends-on] [--source] [--tag] [--git]` — post-hoc link command.
- `specforge promote` — now accepts `--implements`, `--req`, `--test`, `--depends-on`, `--tag` flags; links are set on the promoted artifact in one command.
- Daemon: `POST /artifacts/{id}/link` endpoint with `LinkArtifactRequest`.
- AI adapter: `link_artifact` action in `handle_tool_call`.
- MCP: `link_artifact` tool added to the server tools list.
- Studio: Link… dialog for linking selected artifact.
- Web UI: Link Artifact section; row click fills Link ID field.
- Tests: 172 (was 159).

## 0.9.0

- Performance: `project.artifacts()` now caches by file mtime; cache is invalidated on `create_artifact` and `update_status`. Repeated calls within a command or daemon request return the same list object.
- `specforge check`: CI gate command — runs validation and asserts release gate PASS; exits 1 and prints details on failure. Suitable for CI pipelines.
- README: rewritten to 0.9.0 state — covers all commands, artifact kinds, MCP integration, tags, daemon endpoints, and MCP tool table.
- Tests: 159 (was 149).

## 0.8.0

- MCP stdio server: `specforge_daemon/mcp_server.py` — JSON-RPC 2.0 over stdin/stdout; exposes 9 tools (create_artifact, promote_artifact, update_status, get_artifact, list_artifacts, search, get_status, context_pack, validate) with full JSON Schema definitions.
- CLI `specforge mcp <path>` — starts the MCP server for a project.
- CLI `specforge mcp-config <path>` — prints the Claude Code `mcpServers` config snippet.
- Tests: 149 (was 135).

## 0.7.0

- `specforge status`: project health dashboard — artifact counts by kind with status breakdown, open tasks list, unverified requirements, release gate PASS/FAIL. Rich Panels in CLI.
- `GET /status` daemon endpoint.
- Web UI and Studio: Status button in toolbar.
- Tests: 135 (was 124).

## 0.6.0

- Fixed `specforge list` regression: restored Path column alongside new Tags column.
- Improved `specforge show`: Rich Panel layout with labelled metadata fields, link rows, and body panel — replaces raw JSON dump.
- AI adapter: `specforge_core/adapter.py` — `handle_tool_call(project, call)` dispatches create_artifact, promote_artifact, update_status, get_artifact, list_artifacts, search, context_pack, report, validate; never raises, always returns `{ok, result, error}`.
- CLI `specforge tool-call <path> <json>` — AI adapter entry point from the command line.
- Daemon `POST /tool-call` — AI adapter entry point over HTTP.
- Tests: 124 (was 107).

## 0.5.0

- Tags: `tags` field now written to SQLite `tags` table; `--tag` on all `add-*` commands; `--tag` filter on `list` and `search`; `tag=` filter in `search_artifacts()`; `tags` field in `CreateArtifactRequest`.
- New commands: `add-ref` (REFERENCE), `add-conv` (CONVERSATION) — completes all artifact kind coverage.
- Improved `specforge graph`: Rich tree output showing outgoing/incoming links with link type labels.
- GUI complete: web UI Export/Validate/Git Log buttons + full link fields; Studio Create Artifact dialog + Search + Export/Validate/Git Log buttons.
- Daemon: `CreateArtifactRequest` now carries `implements`, `related_requirements`, and `tags`.
- Tests: 107 (was 96).

## 0.4.0

- Search: `specforge search <path> <query> [--kind] [--status]`; multi-term AND across title + body; snippet per result; daemon `GET /search`; web UI search section.
- Tests: 96 (was 80).

## 0.3.0

- Traceability matrix export: `specforge_core/export.py` with CSV + Markdown output to `trace/exports/`; CLI `specforge export [--format csv|markdown|both]`; daemon `GET /export` and `GET /export/matrix`.
- `specforge init --git`: `git init`, stage scaffold, initial commit.
- Full CLI coverage: `add-decision`, `add-assumption`, `add-constraint`, `add-task`, `add-test`, `add-verification` with link options and `--git`.
- Tests: 46 (was 27 after git integration).

## 0.2.0

- T1: Promotion workflow — `promote_artifact`, `update_status`, `get_artifact` on `Project`; CLI `promote`, `update-status`, `show`; daemon `POST /artifacts/{id}/promote`, `PATCH /artifacts/{id}/status`, `GET /artifacts/{id}`.
- T2: AI context-pack — `build_context_pack` in `specforge_core/contextpack.py`; CLI `context-pack`; daemon `GET /context-pack`.
- T3: Acceptance report — `build_acceptance_report` in `specforge_core/report.py`; CLI `report`; daemon `GET /report`.
- T4: Watch + auto-rebuild — `ProjectWatcher` (watchdog) in `specforge_daemon/watcher.py`; wired into daemon lifespan and `POST /projects/open`.
- Tests: 19 tests (was 5).

## 0.1.0

- Initial daemon + CLI + PySide6 + web starter implementation.
- Added Markdown/YAML artifact storage.
- Added SQLite trace index rebuild.
- Added validation and tests.
