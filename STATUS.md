# SpecForge Status

Updated: 2026-06-01

## Overall

| Area | Status |
|------|--------|
| T1 Promotion workflow | complete |
| T2 AI context-pack | complete |
| T3 Acceptance report | complete |
| T4 Watch + auto-rebuild | complete |

## Tests

```
124 passing, 0 failing
```

## What was added

### T1 — Promotion workflow
- `Project.get_artifact(id)` — find artifact by ID
- `Project.update_status(id, status)` — update status in-place, persists to file
- `Project.promote_artifact(id, target_kind, ...)` — create a new artifact of the target kind with `source=` trace link to the original
- CLI: `specforge promote`, `specforge update-status`, `specforge show`
- Daemon: `POST /artifacts/{id}/promote`, `PATCH /artifacts/{id}/status`, `GET /artifacts/{id}`

### T2 — AI context-pack
- `specforge_core/contextpack.py` — `build_context_pack(project)` returns a JSON-serializable dict with approved requirements, open tasks, decisions, constraints, unverified requirements, and all link edges
- CLI: `specforge context-pack <path> [--output file.json]`
- Daemon: `GET /context-pack`

### T3 — Acceptance report
- `specforge_core/report.py` — `build_acceptance_report(project, index)` returns a Markdown report with requirements coverage table, unverified requirements, open tasks, change orders, and a release gate PASS/FAIL
- CLI: `specforge report <path> [--output report.md]`
- Daemon: `GET /report`

### T4 — Watch + auto-rebuild
- `specforge_daemon/watcher.py` — `ProjectWatcher` uses watchdog to watch the project root for `.md` file changes and auto-rebuilds the trace index
- Wired into `POST /projects/open` — starts watching the newly opened project
- Wired into FastAPI lifespan shutdown — stops the watcher cleanly

### GUI complete
**Web UI** additions: Export Matrix, Validate, Git Log buttons; link fields in Create Artifact (source, implements, related-reqs, verified-by, depends-on); rejected/archived in status dropdown.

**Studio** additions: `CreateArtifactDialog` (all fields including links); Search bar with Enter key support (filters list + shows snippets); Export Matrix, Validate, Git Log buttons; toolbar reorganised into button rows; `urllib.parse` for search query encoding.

**Daemon** fix: `CreateArtifactRequest` now includes `implements` and `related_requirements`, wired into `create_artifact`.

### Polish
- `specforge list --status S` filter added alongside existing `--kind K`
- `README.md` rewritten to cover all current commands, artifact kinds, statuses, daemon endpoints, git integration, and file watcher

### Demo project script
- `scripts/create_demo_project.sh` — 19-step walkthrough of the full lifecycle (init --git → idea → candidate → requirement → decision/assumption/constraint → change order → task → test → verification → archive → trace → validate → search → report → export → context-pack → git log)
- Produces a PASS acceptance report with 3 verified requirements, 0 open tasks
- Idempotent (deletes and recreates output directory each run)
- Fixed `_git_init_project` (`repo.git.add(A=True)` not `repo.index.add(["--all"])`)
- Fixed `typer.Argument("")` for `text` param in `add-idea` / `add-candidate` (Typer 0.26 positional registration)
- Fixed `contextpack.py` to include `verified` requirements in `approved_requirements`

### Search
- `specforge_core/search.py` — `search_artifacts(project, query, kinds, statuses)`: multi-term AND across `title` + `body` via SQLite LIKE; returns id, kind, status, title, snippet, path
- Snippet shows the first matching line (truncated to 120 chars)
- CLI: `specforge search <path> <query> [--kind K] [--status S]`
- Daemon: `GET /search?q=...&kind=...&status=...`
- Web UI: Search section with keyword input

### Daemon integration tests
- `tests/test_daemon.py` — 34 tests covering all 15 endpoints: health, UI, 400 guards, project open, artifact CRUD, promote, update-status, trace rebuild + graph, context-pack, report, export, git log, validate
- `reset_daemon` autouse fixture resets global state and patches `ProjectWatcher.start` to a no-op — eliminates background-thread races against explicit rebuild calls
- Fixed `ProjectWatcher` to skip non-artifact `.md` files (e.g. `memory.md`) using `ID_RE` pattern check
- Added `PRAGMA journal_mode=WAL` and `timeout=15` to all SQLite connections in `trace.py`

### Traceability matrix export
- `specforge_core/export.py` — `build_matrix` (reverse-maps tasks/tests/verifications/decisions/change-orders back to requirements), `to_csv`, `to_markdown`, `export_project` (writes timestamped files to `trace/exports/`)
- CLI: `specforge export <path> [--format csv|markdown|both]`
- Daemon: `GET /export`, `GET /export/matrix?fmt=markdown`
- `specforge init --git` — `git init` + stage all scaffold files + initial commit

### Full CLI coverage
- `add-decision` — `--text`, `--source`, `--req` (repeatable), `--git`; status defaults to `approved`
- `add-assumption` — same shape as `add-decision`
- `add-constraint` — same shape as `add-decision`
- `add-task` — `--text`, `--implements` (repeatable), `--depends-on` (repeatable), `--git`
- `add-test` — `--text`, `--req` (repeatable), `--git`
- `add-verification` — `--text`, `--req` (repeatable), `--test` (repeatable), `--git`

### Git integration
- `specforge_core/gitwrap.py` — `find_repo`, `commit_artifact`, `artifact_log` (thin GitPython wrapper; silently skips if no repo)
- `git_commit: bool = False` on `create_artifact`, `update_status`, `promote_artifact`
- CLI: `--git` flag on all write commands; `specforge log` command with Rich table output
- Daemon: `git_commit` field on `CreateArtifactRequest`, `PromoteRequest`, `UpdateStatusRequest`; `GET /git/log`

### Web UI + Studio (wired in follow-up)
- `specforge_web/index.html` — Promote, Update Status, Context Pack, Acceptance Report; artifact rows clickable to fill ID fields
- `specforge_studio/main.py` — Promote dialog, Update Status dialog, Context Pack button, Acceptance Report button; `patch_json` helper for PATCH requests

## Version

0.2.0 — promotion workflow, AI context-pack, acceptance report, watch + auto-rebuild
