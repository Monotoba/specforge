# Traceability Reference

Traceability is the ability to follow the thread of a requirement from
its origin to its implementation to the evidence that proves it works.
This document describes SpecForge's traceability model in detail.

For the theory behind traceability, see [THEORY.md](THEORY.md).

---

## The complete traceability path

A fully-traced requirement follows this path:

```
Conversation or stakeholder request
    │ captured as
    ▼
Idea artifact (IDEA-NNNN)
    │ promoted to
    ▼
Candidate artifact (CAND-NNNN)  ─── linked to ──► Reference (REF-NNNN)
    │ promoted to
    ▼
Requirement artifact (REQ-NNNN) ─── linked to ──► Decision (DEC-NNNN)
    │                                              Assumption (ASMP-NNNN)
    │                                              Constraint (CON-NNNN)
    │ implemented by
    ▼
Task artifact (TASK-NNNN)
    │ verified by
    ▼
Test artifact (TEST-NNNN)
    │ evidenced by
    ▼
Verification artifact (VER-NNNN)
```

Not every path needs every node. A simple requirement might go
directly from idea to requirement with a single task and one
verification. A complex safety-critical feature might have multiple
candidates, several decisions, external references to standards, and
multiple tests with multi-environment verification evidence.

---

## Link types

| Field | Carried by | Points to | Meaning |
|-------|-----------|-----------|---------|
| `source` | Any | Any | Provenance: "this was created from that" |
| `implements` | task, decision | requirement | "this implements that requirement" |
| `related_requirements` | decision, assumption, constraint, test, verification | requirement | "this relates to these requirements" |
| `verified_by` | requirement, test | verification | "this is evidenced by these verifications" |
| `depends_on` | task | task | "this task cannot start until those are done" |
| `tags` | Any | — | Free-form labels for filtering |

---

## Completeness checks

SpecForge's validation checks the following traceability conditions:

1. **Linked artifacts exist**: every ID in a link field must correspond
   to an existing artifact. A link to a deleted or mistyped ID is a
   validation error.

2. **Bidirectional consistency**: if TASK-0001 has `implements:
   [REQ-0001]`, then REQ-0001 should be traceable to TASK-0001 via
   the graph query (not stored as a field, but computed from the index).

3. **Verification coverage**: a requirement in `approved` or later
   status that has no verification artifacts linked to it will block
   the release gate.

---

## The traceability matrix

The export command generates a matrix showing, for each requirement,
every task that implements it and every verification artifact that
covers it:

```bash
specforge export ./proj --format markdown
```

```markdown
| Requirement | Tasks | Verifications |
|-------------|-------|---------------|
| REQ-0001: Export DXF files | TASK-0001, TASK-0002 | VER-0001 |
| REQ-0002: Batch export | TASK-0003 | VER-0001 |
```

This matrix is the standard output required by certification processes
(ISO 26262, IEC 62443, DO-178C, FDA 21 CFR Part 11). The CSV format
is suitable for import into external quality management systems.

---

## Change orders and traceability

A change order (CO) provides traceability for requirement changes.
When a requirement must change after approval:

1. Create a CO linked to the affected requirement
2. Record the reason, proposed change, and impact assessment
3. Review and approve the CO
4. Update the requirement body and reset to `approved`
5. Archive the CO with the approval record

The CO remains in the project history permanently. Anyone who reads
the requirement in the future can see that it was changed, why it was
changed, and what the previous version said (via git history).

---

## Querying the trace graph

The CLI provides several ways to navigate the traceability graph:

```bash
# Show all links for an artifact
specforge show ./proj REQ-0001

# Show the full link tree (outgoing and incoming)
specforge graph ./proj REQ-0001

# Search by linked ID (find everything related to REQ-0001)
specforge search ./proj REQ-0001

# List all tasks implementing a specific requirement
specforge list ./proj --kind task
# (filter manually by looking at implements fields)
```

The daemon REST API provides graph queries:

```
GET /trace/{artifact_id}   → full link graph as JSON
GET /search?q={term}       → full-text search results
```
