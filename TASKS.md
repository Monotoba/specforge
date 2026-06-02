# SpecForge Task List

## T1 — Promotion workflow

Advance artifacts through stages with explicit trace links. Each promotion creates or updates artifacts rather than silently mutating fields.

### Subtasks

- [x] T1.1 `Project.promote_artifact(artifact_id, target_kind, **overrides)` — creates a new artifact of `target_kind` with `source=` pointing at the original; sets appropriate default status
- [x] T1.2 `Project.update_status(artifact_id, new_status)` — update status of an existing artifact in-place
- [x] T1.3 CLI `specforge promote <path> <id> <target-kind>` command
- [x] T1.4 CLI `specforge update-status <path> <id> <status>` command
- [x] T1.5 Daemon `POST /artifacts/{id}/promote` and `PATCH /artifacts/{id}/status`
- [x] T1.6 Tests for promotion round-trips

## T2 — AI context-pack

Build a JSON bundle that captures the active project state for AI agents.

### Subtasks

- [x] T2.1 `specforge_core/contextpack.py` — `build_context_pack(project)` returns structured dict
  - approved requirements with bodies
  - open tasks (status != archived/verified)
  - unverified requirements list
  - recent decisions and constraints
  - all inter-artifact links summary
- [x] T2.2 CLI `specforge context-pack <path> [--output file.json]`
- [x] T2.3 Daemon `GET /context-pack`
- [x] T2.4 Tests for context-pack structure

## T3 — Acceptance report

Generate a human-readable Markdown report summarising release readiness.

### Subtasks

- [x] T3.1 `specforge_core/report.py` — `build_acceptance_report(project, index)` returns Markdown string
  - requirements coverage table (verified / total)
  - per-requirement row: ID, title, status, verified_by IDs
  - unverified requirements section
  - open tasks section
  - change orders summary
  - footer with generation timestamp
- [x] T3.2 CLI `specforge report <path> [--output report.md]`
- [x] T3.3 Daemon `GET /report`
- [x] T3.4 Tests for report structure

## T4 — Watch + auto-rebuild

Daemon watches the open project directory and rebuilds the trace index on any artifact file change.

### Subtasks

- [x] T4.1 `specforge_daemon/watcher.py` — `ProjectWatcher` using watchdog; calls `TraceIndex.rebuild()` on `.md` file events
- [x] T4.2 Wire watcher into daemon startup in `specforge_daemon/main.py`; stop watcher on shutdown
- [x] T4.3 Wire watcher start/stop into `POST /projects/open`
- [x] T4.4 Tests (mock watchdog or use tmp_path with a short delay)
