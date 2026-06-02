# Artifact Reference

Every piece of knowledge in a SpecForge project is an **artifact** — a
Markdown file with YAML front matter. Artifacts link to each other through
named relationship fields, forming a traceable graph from raw ideas to
verified requirements.

---

## Artifact kinds

### idea
A raw exploration note. No formal structure required. Use ideas to
capture anything worth remembering before you know whether it matters.

- Default status: `draft`
- Typical next step: promote to `candidate`

### candidate
An idea that has passed initial evaluation and is being considered for
formalisation. More structured than an idea but not yet a committed
requirement.

- Default status: `proposed`
- Typical next step: promote to `requirement`

### requirement
A formally approved requirement. Every requirement must eventually be
`implemented` (linked to tasks) and `verified` (linked to verification
evidence) before the release gate will pass.

- Default status: `approved`
- Key links: `implements` (tasks), `verified_by` (verifications)

### decision
An architectural or design decision with rationale. Records the *why*
behind a technical choice.

- Default status: `approved`
- Key links: `related_requirements`

### assumption
A stated assumption that the project depends on. Assumptions should be
reviewed and either confirmed or converted to constraints.

- Default status: `draft`
- Key links: `related_requirements`

### constraint
A non-negotiable constraint — legal, technical, organisational, or
physical. Constraints bound what solutions are acceptable.

- Default status: `draft`
- Key links: `related_requirements`

### change_order
A proposed change to scope, a requirement, or a decision. Tracks
the lifecycle of "we want to change X" through approval or rejection.

- Default status: `proposed`

### task
A development work item. Tasks implement requirements and drive the
project toward `implemented` and then `verified` status.

- Default status: `draft`
- Key links: `implements` (requirements), `depends_on` (other tasks)

### test
A test specification linked to one or more requirements. Defines what
must be tested, not how — the *how* is up to the team.

- Default status: `draft`
- Key links: `related_requirements`

### verification
Evidence that a requirement has been met — test results, QA sign-off,
CI logs, or bench measurements. A requirement reaches `verified` status
when it has at least one verification artifact pointing to it.

- Default status: `draft`
- Key links: `related_requirements`, `verified_by` (tests)

### reference
An external reference: a URL, document, paper, standard, or data sheet.
Use references to anchor decisions and requirements to primary sources.

- Default status: `draft`

### conversation
A recorded conversation note or AI session summary. Captures context
that might otherwise be lost in email or chat.

- Default status: `draft`

---

## Status lifecycle

```
draft ──► proposed ──► approved ──► implemented ──► verified
                                 │
                                 └──► rejected
                                 └──► archived
```

Any artifact can move to `rejected` or `archived` at any point.

| Status | Meaning |
|--------|---------|
| `draft` | Work in progress, not yet ready for review |
| `proposed` | Ready for review or evaluation |
| `approved` | Formally accepted — requirements start here |
| `implemented` | Code or work is done; awaiting verification |
| `verified` | Acceptance evidence recorded; requirement is closed |
| `rejected` | Deliberately not accepted or descoped |
| `archived` | Completed or no longer relevant; kept for history |

---

## Artifact fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-assigned (e.g. `REQ-0001`) |
| `kind` | enum | Artifact kind (see above) |
| `title` | string | Short, descriptive title |
| `status` | enum | Current lifecycle status |
| `body` | markdown | Main content of the artifact |
| `source` | ID | Artifact this was promoted from |
| `implements` | ID list | Requirements this task implements |
| `related_requirements` | ID list | Requirements this artifact relates to |
| `related_decisions` | ID list | Decisions this artifact relates to |
| `related_assumptions` | ID list | Assumptions this artifact relates to |
| `depends_on` | ID list | Artifacts this one depends on |
| `dependents` | ID list | Artifacts that depend on this one |
| `verified_by` | ID list | Verifications or tests that cover this |
| `references` | ID list | Reference artifacts |
| `tags` | string list | Free-form labels for filtering |
| `created_at` | datetime | When the artifact was created |
| `updated_at` | datetime | When the artifact was last modified |

---

## ID format

IDs follow the pattern `<KIND_PREFIX>-<NNNN>`:

| Kind | Prefix |
|------|--------|
| idea | `IDEA` |
| candidate | `CAND` |
| requirement | `REQ` |
| decision | `DEC` |
| assumption | `ASMP` |
| constraint | `CON` |
| change_order | `CO` |
| task | `TASK` |
| test | `TEST` |
| verification | `VER` |
| reference | `REF` |
| conversation | `CONV` |

IDs are assigned sequentially within each kind and are permanent.
