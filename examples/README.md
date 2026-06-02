# Examples

## Demo project

Run the full lifecycle demo:

```bash
./scripts/create_demo_project.sh            # writes to examples/demo_project
./scripts/create_demo_project.sh /tmp/demo  # custom output directory
```

The script is idempotent — it removes and recreates the output directory each run.

### What it demonstrates

| Step | Command | Result |
|------|---------|--------|
| 1 | `specforge init --git` | Scaffold + initial commit |
| 2 | `add-idea` × 3 | Three exploration ideas |
| 3 | `promote … candidate` × 2 | Incubation candidates with trace links |
| 4 | `add-req` × 3 | Approved requirements |
| 5 | `add-decision`, `add-assumption`, `add-constraint` | Supporting spec artifacts |
| 6 | `add-co` | Proposed change order |
| 7 | `add-task` × 3 | Tasks linked via `--implements` and `--depends-on` |
| 8 | `update-status` × 6 | Tasks and requirements → implemented |
| 9 | `add-test` × 3 | Test definitions linked via `--req` |
| 10 | `add-verification` × 2 | Verification evidence linking tests to requirements |
| 11 | `update-status` × 3 | Requirements → verified |
| 12 | `update-status` × 3 | Tasks → archived |
| 13 | `specforge trace` | Rebuilt SQLite trace index |
| 14 | `specforge validate` | Zero errors |
| 15 | `specforge search` | Keyword search across titles and bodies |
| 16 | `specforge report` | Acceptance report — **PASS** |
| 17 | `specforge export` | Traceability matrix (CSV + Markdown) |
| 18 | `specforge context-pack` | JSON bundle for AI agents |
| 19 | `specforge log` | Git history of all artifact commits |

### Output files

After the script completes, `examples/demo_project/` contains:

```
ACCEPTANCE_REPORT.md          — release-gate report
context_pack.json             — AI context bundle
trace/exports/traceability-*  — CSV and Markdown traceability matrix
trace/traceability.sqlite     — SQLite trace index (gitignored)
exploration/idea-log/         — IDEA-000* artifact files
incubation/candidates/        — CAND-000* artifact files
specification/requirements/   — REQ-000* artifact files
specification/decisions/      — DEC-000* artifact files
...
```
