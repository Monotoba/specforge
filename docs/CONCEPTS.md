# Core Concepts

This document defines the fundamental concepts and terminology used
throughout SpecForge. Reading this before the process guide will make
the methodology easier to follow.

---

## Project

A SpecForge **project** is a directory on the filesystem. It contains
a standard folder hierarchy of artifact files, a SQLite trace index,
and a configuration file. There is no central server, no database
server, no cloud account — everything lives in one directory that can
be backed up, copied, or committed to git.

```
my-project/
├── .specforge.yaml          ← project configuration
├── .specforge/
│   ├── plugins/             ← local Python plugins
│   └── templates/           ← artifact body templates
├── exploration/
│   └── idea-log/            ← idea artifacts
├── specification/
│   ├── requirements/        ← requirement artifacts
│   ├── decisions/           ← decision artifacts
│   ├── assumptions/         ← assumption artifacts
│   └── constraints/         ← constraint artifacts
├── development/
│   ├── work-log/tasks/      ← task artifacts
│   └── test-logs/tests/     ← test artifacts
│       └── verifications/   ← verification artifacts
└── trace/
    └── traceability.sqlite  ← query index (excluded from git)
```

---

## Artifact

An **artifact** is the fundamental unit of information in a SpecForge
project. Every idea, requirement, task, test, and piece of verification
evidence is an artifact.

On disk, an artifact is a Markdown file with YAML front matter:

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
verified_by: []
depends_on: []
tags: [v1.0, export]
---

## Purpose

The system shall export project drawings as DXF files compatible with
AutoCAD 2018 and later.

## Acceptance criteria

- Exported files open without errors in AutoCAD 2018+
- All drawing layers are preserved
- Export completes within 10 seconds for drawings up to 100 entities
```

The YAML front matter is the structured metadata. The Markdown body is
the human-readable content. Both are plain text; both are version-controlled.

---

## Artifact kind

The **kind** of an artifact determines its role in the project and its
position in the traceability graph.

### idea
The starting point of all work. Ideas are raw, unstructured, and
cheap to create. They exist to capture knowledge before it is lost.
An idea might be a user pain point, a technical possibility, a
stakeholder request, or a wild thought during a design session.

**Rule of thumb**: if you have a thought about the project and it
might matter later, make it an idea.

### candidate
An idea that has been evaluated and is being considered for
formalisation. A candidate has enough detail to assess feasibility
and business value. It has not yet been committed to as a requirement.

### requirement
A formally approved statement of what the system must do, structured
to be unambiguous, verifiable, and traceable. Requirements are the
anchor of the entire traceability graph — everything else links to them.

### decision
A recorded architectural or design choice with rationale. Decisions
explain *why* the system is built the way it is, not just *what* was
built.

### assumption
A stated belief about the operating environment or context that the
project depends on. Assumptions are things that are not within the
project's control but must be true for the project to succeed.

### constraint
A non-negotiable boundary that restricts the solution space.
Constraints come from regulatory requirements, hardware limits,
business rules, or contractual obligations.

### change_order
A proposed modification to an existing requirement. Change orders
provide an audit trail for scope changes and allow changes to be
reviewed before they are applied.

### task
A unit of implementation work. Tasks implement requirements. They
are assigned to people, estimated, and tracked to completion.

### test
A specification of what to test, under what conditions, with what
expected result. Tests are written during or before implementation.

### verification
Evidence that a requirement has been satisfied. A verification artifact
records who tested what, when, with what result, in what environment.

### reference
An external source — a URL, document, standard, data sheet, or paper —
that informed or constrains the project.

### conversation
A recorded discussion: meeting notes, stakeholder interview transcripts,
AI session summaries.

---

## Status

Every artifact has a **status** that indicates where it is in its
lifecycle.

```
draft → proposed → approved → implemented → verified
                           ↘ rejected
                           ↘ archived
```

| Status | Meaning | Typical next action |
|--------|---------|-------------------|
| `draft` | Work in progress | Review and promote |
| `proposed` | Ready for decision | Approve or reject |
| `approved` | Formally accepted | Implement |
| `implemented` | Built, awaiting verification | Test and verify |
| `verified` | Acceptance evidence recorded | Archive or release |
| `rejected` | Explicitly not accepted | Record reason, archive |
| `archived` | Completed or no longer relevant | No action needed |

Not all statuses are used by all kinds. A `task` goes draft →
proposed → implemented → archived. A `requirement` goes approved →
implemented → verified.

---

## Traceability links

Artifacts connect to each other through **link fields**. These fields
create a queryable graph that supports impact analysis, completeness
checking, and traceability reports.

| Field | Direction | Meaning |
|-------|-----------|---------|
| `source` | → parent | "This artifact was created from this one" |
| `implements` | → requirement | "This task/decision implements this requirement" |
| `related_requirements` | → requirements | "This artifact is related to these requirements" |
| `verified_by` | → verifications | "This requirement/test is evidenced by these verifications" |
| `depends_on` | → tasks | "This task cannot start until these tasks are done" |
| `dependents` | ← tasks | "These tasks depend on this one" (usually auto-managed) |
| `tags` | — | Free-form labels for filtering and grouping |

Links use artifact IDs. They are stored in the YAML front matter and
are checked during validation.

---

## The trace index

The **trace index** is a SQLite database that mirrors the artifact
graph in a queryable form. It stores artifacts, their links, their
bodies (for full-text search), and their tags.

The trace index is rebuilt from the artifact files whenever you run
`specforge trace ./proj` or click **Rebuild Trace** in the UI. It is
excluded from git because it is derived — it can always be reconstructed
from the source files.

The trace index enables:
- Fast full-text search across all artifact bodies and titles
- Graph queries (find all tasks implementing REQ-0001)
- Traceability matrix export
- Validation of link integrity

---

## The release gate

The **release gate** is a binary check that must pass before software
is considered ready to ship.

**Pass conditions:**
1. Every requirement in `approved`, `implemented`, or `verified` status
   has at least one verification artifact linked to it with `verified`
   status.
2. There are no tasks in `draft`, `proposed`, or `implemented` status.

If either condition fails, the gate fails, and the output identifies
exactly which requirements and tasks are blocking release.

```bash
specforge check ./proj    # exits 0 (PASS) or 1 (FAIL)
```

---

## The acceptance report

The **acceptance report** is a structured Markdown document generated
by SpecForge that summarises the project state for stakeholder sign-off
or regulatory submission. It lists every requirement, its status, and
its linked verification evidence.

```bash
specforge report ./proj --output ./proj/ACCEPTANCE_REPORT.md
```

---

## The context pack

The **context pack** is a structured JSON document that assembles the
most important project information in a format optimised for consumption
by large language models.

```json
{
  "project_name": "Drawing Export System",
  "artifact_count": 42,
  "approved_requirements": [{ "id": "REQ-0001", "title": "...", "body": "..." }],
  "open_tasks": [...],
  "unverified_requirements": [...],
  "recent_decisions": [...]
}
```

Use the context pack to give an AI assistant instant, complete project
context at the start of a conversation.

---

## Plugins

**Plugins** are local Python files in `.specforge/plugins/*.py` that
are called after every artifact mutation. They can perform any action
that Python can perform: logging, notifications, auto-tagging, syncing
to external systems.

A plugin defines one function:

```python
def on_event(event: str, artifact, project) -> None:
    """Called after each mutation. Exceptions are caught and logged."""
```

---

## Webhooks

**Webhooks** are HTTP callbacks registered in `.specforge.yaml`. After
each artifact mutation, SpecForge POSTs a JSON payload to every
registered URL whose event filter matches the event type.

Webhooks are delivery mechanisms for external integrations: Slack
notifications, CI triggers, dashboard updates.

---

## Templates

**Templates** are Markdown files in `.specforge/templates/<kind>.md`
that provide default body content for new artifacts. They can include
optional YAML front matter to preset tags and status.

Templates reduce the friction of creating well-structured artifacts
and ensure consistency across a team.

---

## AI drafting

**AI drafting** is the `specforge draft` command, which calls a
configured LLM (Anthropic, OpenAI, or local Ollama) to generate
artifact body content from a free-form prompt.

The AI produces a first draft; the human reviews and confirms. The
interaction keeps humans in control of every artifact while eliminating
the blank-page problem.

---

## MCP integration

**MCP (Model Context Protocol)** is a standard for connecting AI
assistants to external tools. The `specforge mcp` command starts an
MCP server that exposes 11 SpecForge tools to Claude Code.

With MCP configured, Claude Code can read and write project artifacts
directly during a conversation. This closes the loop between
requirements and implementation — an AI assistant can always answer
"what requirement does this code implement?" and "what work remains
before we can release?"
