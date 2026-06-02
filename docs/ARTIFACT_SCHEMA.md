# Artifact File Schema

Every SpecForge artifact is stored as a UTF-8 Markdown file with YAML
front matter. This document describes the complete schema.

---

## File format

```markdown
---
id: REQ-0001
kind: requirement
title: Export DXF files
status: approved
created_at: "2026-06-01T10:00:00+00:00"
updated_at: "2026-06-01T14:30:00+00:00"
source: CAND-0001
implements: []
related_requirements: []
related_decisions: []
related_assumptions: []
depends_on: []
dependents: []
verified_by: []
references: []
tags: [v1.0, export]
---

## Purpose

The system shall export project drawings as DXF files compatible with
AutoCAD 2018 and later versions.

## Acceptance criteria

- Exported files open without errors in AutoCAD 2018+
- All drawing layers are preserved in the exported file
```

---

## Field reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique, permanent artifact ID (e.g. `REQ-0001`) |
| `kind` | enum | Artifact kind — see table below |
| `title` | string | Short, descriptive title |
| `status` | enum | Lifecycle status — see table below |
| `created_at` | ISO 8601 datetime | When the artifact was first created |
| `updated_at` | ISO 8601 datetime | When the artifact was last modified |
| `source` | ID or null | The artifact this was created from (provenance) |
| `implements` | list of IDs | Requirements this task/decision implements |
| `related_requirements` | list of IDs | Related requirement artifacts |
| `related_decisions` | list of IDs | Related decision artifacts |
| `related_assumptions` | list of IDs | Related assumption artifacts |
| `depends_on` | list of IDs | Tasks that must complete before this one |
| `dependents` | list of IDs | Tasks that depend on this one |
| `verified_by` | list of IDs | Verification/test artifacts covering this |
| `references` | list of IDs | Reference artifacts cited by this |
| `tags` | list of strings | Free-form labels for filtering |

---

## ID prefixes

| Kind | Prefix | Example |
|------|--------|---------|
| idea | `IDEA` | `IDEA-0001` |
| candidate | `CAND` | `CAND-0001` |
| requirement | `REQ` | `REQ-0001` |
| decision | `DEC` | `DEC-0001` |
| assumption | `ASMP` | `ASMP-0001` |
| constraint | `CON` | `CON-0001` |
| change_order | `CO` | `CO-0001` |
| task | `TASK` | `TASK-0001` |
| test | `TEST` | `TEST-0001` |
| verification | `VER` | `VER-0001` |
| reference | `REF` | `REF-0001` |
| conversation | `CONV` | `CONV-0001` |

IDs are four-digit zero-padded numbers within each kind, allocated
sequentially. Once assigned, an ID is never reused.

---

## Status values

| Value | Meaning |
|-------|---------|
| `draft` | Work in progress |
| `proposed` | Ready for review |
| `approved` | Formally accepted |
| `implemented` | Built; awaiting verification |
| `verified` | Acceptance evidence recorded |
| `rejected` | Explicitly not accepted |
| `archived` | Completed or no longer relevant |

---

## File naming and location

Artifact files are named `<id>-<slug>.md` where the slug is the title
lowercased with spaces replaced by hyphens. They are stored in
kind-specific subdirectories:

```
exploration/idea-log/IDEA-0001-offline-support.md
specification/requirements/REQ-0001-export-dxf-files.md
development/work-log/tasks/TASK-0001-implement-dxf-exporter.md
```

The file path is not stored in the YAML — it is determined at load time
from the file's location on disk.

---

## Body content

The Markdown body follows the closing `---` of the front matter. There
is no required structure — write whatever is appropriate for the
artifact kind. Common patterns:

**Requirement**: `## Purpose`, `## Acceptance criteria`

**Decision**: `## Rationale`, `## Alternatives considered`,
`## Rejected alternatives`

**Task**: `## What`, `## Done when`, `## Notes`

**Test**: `## Objective`, `## Prerequisites`, `## Steps`,
`## Expected result`

**Verification**: `## Result`, date, environment, measurements or
pass/fail details, build number, tester name
