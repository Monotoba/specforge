# Project Directory Structure

A SpecForge project is a standard directory layout. The structure
separates informal exploration from controlled specification and
provides dedicated areas for each phase of the development lifecycle.

---

## Full structure

```
<project-root>/
│
├── .specforge.yaml                  ← Project configuration
│
├── .specforge/
│   ├── plugins/                     ← Local Python event plugins
│   │   └── example_plugin.py.disabled
│   └── templates/                   ← Artifact body templates
│       ├── requirement.md
│       ├── task.md
│       └── test.md
│
├── exploration/
│   ├── memory.md                    ← Long-term exploration notes
│   ├── idea-log/                    ← IDEA-NNNN artifacts
│   └── references/                  ← REF-NNNN artifacts
│
├── incubation/
│   ├── memory.md                    ← Structured evaluation notes
│   ├── candidates/                  ← CAND-NNNN artifacts
│   ├── investigations/              ← (reserved)
│   └── evaluations/                 ← (reserved)
│
├── specification/
│   ├── memory.md                    ← Requirements policy notes
│   ├── requirements/                ← REQ-NNNN artifacts
│   ├── decisions/                   ← DEC-NNNN artifacts
│   ├── assumptions/                 ← ASMP-NNNN artifacts
│   ├── constraints/                 ← CON-NNNN artifacts
│   ├── interfaces/                  ← (reserved for ICD artifacts)
│   └── acceptance/                  ← (reserved for acceptance criteria docs)
│
├── change-orders/
│   ├── proposed/                    ← CO-NNNN artifacts (proposed)
│   ├── approved/                    ← (reserved)
│   ├── rejected/                    ← (reserved)
│   └── archived/                    ← (reserved)
│
├── development/
│   ├── work-log/
│   │   ├── entries/                 ← (work log entries)
│   │   └── tasks/                   ← TASK-NNNN artifacts
│   ├── changelog/                   ← (release notes)
│   ├── test-logs/
│   │   ├── tests/                   ← TEST-NNNN artifacts
│   │   └── runs/                    ← (test run logs)
│   └── verification-logs/
│       ├── verifications/           ← VER-NNNN artifacts
│       └── runs/                    ← (verification run logs)
│
├── conversation-vault/
│   ├── sessions/                    ← CONV-NNNN artifacts
│   ├── summaries/                   ← (conversation summaries)
│   └── extracted-decisions/         ← (decisions extracted from convs)
│
└── trace/
    ├── traceability.sqlite          ← Rebuilt index (not in git)
    └── exports/
        ├── traceability.csv
        └── traceability.md
```

---

## Design rationale

### Separation of phases

The top-level directories map to the phases of the development
lifecycle:

- `exploration/` — informal, unfiltered capture (ideas, references)
- `incubation/` — evaluated candidates heading toward formalisation
- `specification/` — controlled, approved requirements and decisions
- `change-orders/` — proposed changes to approved requirements
- `development/` — implementation tasks, tests, verification evidence
- `conversation-vault/` — context from meetings and AI sessions

This separation means a reader can quickly find formal requirements
(always in `specification/requirements/`) without wading through
exploratory notes.

### Memory files

Each phase directory contains a `memory.md` file for free-form notes
that do not belong to a specific artifact: vocabulary, background
context, rejected directions, links to external resources. These are
not artifacts — they have no ID or status. They are notes for the team.

### Canonical data vs. derived data

All `.md` files are **canonical** — they are the source of truth and
are committed to git. The SQLite database at `trace/traceability.sqlite`
is **derived** — it is built from the `.md` files and is excluded from
git via `.gitignore`. It can always be rebuilt:

```bash
specforge trace ./proj    # rebuild from scratch
```

The export files in `trace/exports/` are also derived and should be
regenerated before sharing. They can be committed to git if desired
(e.g., to track the traceability matrix in version control).

---

## .gitignore

`specforge init` creates a `.gitignore` with:

```
trace/traceability.sqlite
.venv/
__pycache__/
```

Everything else — including the memory files, all artifact files, and
the configuration — is committed to git.
