# Requirements Engineering Theory

## Why specifications matter

Software and hardware projects fail in predictable ways. Studies
consistently show that most defects — often more than 60% — originate
not in code, but in requirements: things that were never written down,
were written ambiguously, or conflicted with each other and nobody
noticed until integration. Writing code is fast and cheap compared to
discovering, six months into a project, that the system was built to
satisfy a requirement that nobody actually had.

The root problem is this: **a requirement that exists only in someone's
head cannot be reviewed, challenged, traced, or verified.** It has no
record of why it was chosen, no link to the work that implements it, and
no evidence that it was ever satisfied. When something breaks, or when
a stakeholder asks "does the system do X?", there is no way to answer
with confidence.

Requirements engineering is the practice of making implicit knowledge
explicit. It creates a shared, written contract between the people who
want something and the people who build it.

---

## The cost curve

Barry Boehm's foundational research (later replicated many times across
industries) established what practitioners call the **cost-of-change
curve**: the later in a project a defect is discovered, the more
expensive it is to fix.

```
Cost to fix
    │
100x│                                          ●  Production
    │                                    ●  System test
 10x│                              ●  Integration
    │                        ●  Unit test
  1x│                  ●  Design
    │            ●  Requirements
    │──────────────────────────────────────────── Phase
         Req   Design  Code  Unit  Integ  Prod
```

A requirements defect caught during the specification phase might cost
one hour to fix. The same defect discovered in production can cost
100 to 1000 times more — rework, retesting, deployment, customer impact,
and lost trust. This is why investing in precise, traceable requirements
before writing code is not overhead — it is risk reduction.

SpecForge is designed around this insight. Every artifact — every idea,
requirement, task, test, and verification — is recorded when the cost
of changing it is low.

---

## The V-Model

The V-model is a development lifecycle framework that maps each
construction phase to a corresponding verification phase. It is called
the V-model because the flow of activities forms a V shape:

```
Requirements ──────────────────────────── Acceptance Test
     │                                          │
  Functional Spec ─────────────── System Test  │
          │                           │         │
       Architecture ─── Integration  │         │
               │              │      │         │
             Design ─── Unit Test    │         │
                    │                │         │
                Implementation       │         │
```

The left arm descends through increasing levels of detail:
- **Requirements** define what the system must do
- **Functional specification** translates requirements into system behaviour
- **Architecture** defines how the system is structured
- **Detailed design** specifies component internals
- **Implementation** is the code itself

The right arm ascends through verification levels:
- **Unit tests** verify individual components in isolation
- **Integration tests** verify that components work together
- **System tests** verify the complete system against the specification
- **Acceptance tests** verify that the system satisfies the original requirements

The crucial insight of the V-model is the **horizontal connections**:
each level on the left arm has a corresponding verification level on the
right arm. Requirements must be verifiable — if you cannot test it, you
cannot know it was satisfied. Every requirement needs a test.

SpecForge implements the outer edges of the V: requirements at the top
left, acceptance evidence at the top right, with full traceability
connecting them through tasks and tests.

---

## Traceability

**Traceability** is the ability to follow the thread of a requirement
from its origin, through every design and implementation decision, to
the test evidence that proves it was satisfied. There are three kinds:

### Forward traceability (requirements to implementation)
Starting from a requirement, you can find every design decision,
implementation task, and test that addresses it.

```
REQ-0001  "Export DXF files"
  ├── DEC-0001  "Use ezdxf library"
  ├── TASK-0001  "Implement DXF exporter"
  ├── TASK-0002  "Add batch export CLI flag"
  └── TEST-0001  "DXF round-trip test"
       └── VER-0001  "CI green, build #147"
```

### Backward traceability (implementation to requirements)
Starting from a test or task, you can find the requirement it satisfies.
This answers the question: "why does this code exist?"

### Horizontal traceability (requirement to requirement)
Requirements are not islands. They interact with decisions, assumptions,
and constraints. Horizontal traceability maps these relationships and
makes impact analysis possible: "if we change REQ-0001, what else is
affected?"

### Why traceability matters in practice

**Impact analysis**: Before changing a requirement, you can see
everything that depends on it. Without traceability, changes are
guesses.

**Certification and audit**: Safety-critical industries (aerospace,
medical devices, automotive, defence) require documented traceability
chains as part of regulatory approval. SpecForge's export produces the
matrices these processes require.

**Completeness checking**: The release gate catches requirements with
no tasks implementing them, and requirements with no verification
evidence. A requirement that cannot be traced to a test cannot be
called satisfied.

**Onboarding**: New team members can follow the traceability graph to
understand not just what the system does, but why each part was built
the way it was.

---

## Artifact-centred knowledge management

Traditional project management stores work items (tasks) in one tool,
requirements in another (or in a document), tests in a third, and
decisions in email threads and Slack conversations. Nothing connects.
When a requirement changes, finding everything it affects requires
manual archaeology.

SpecForge uses a single, unified artifact model. Everything — ideas,
requirements, decisions, tasks, tests, verification evidence —
is an artifact with a unique ID, a status, a body, and a set of typed
link fields. The links create a queryable graph. The IDs make every
reference precise and permanent.

This design has several consequences:

**Plain files**: Every artifact is a Markdown file with YAML front
matter. There is no database to back up, no binary format to migrate,
no vendor to depend on. The project lives in your git repository.

**Git history**: Because artifacts are files, git is the audit trail.
You can see exactly when a requirement was created, when it was approved,
who changed its status, and what the body looked like at any point in
history.

**AI-readable**: Plain Markdown is the native format for large language
models. SpecForge's context pack assembles a structured JSON summary
of the project that gives an AI assistant instant, complete project
context. The MCP integration lets Claude Code read and write artifacts
directly during a conversation.

---

## Verification versus testing

These terms are often confused:

**Testing** is the act of running the system and observing its
behaviour. It produces evidence.

**Verification** is the determination, based on evidence, that a
requirement has been satisfied.

A test artifact in SpecForge is a specification: *what* to test, under
*what conditions*, with *what expected result*. It is written during the
specification phase, before implementation — this forces you to think
about whether the requirement is actually testable.

A verification artifact records the *outcome* of running a test:
pass/fail, test environment, build number, tester, date. It is created
after testing. When a verification artifact points to a requirement, it
constitutes formal evidence that the requirement is satisfied.

This separation matters because:
- A test that has not been run proves nothing
- A requirement that has no test cannot be verified
- Verification evidence persists even when the test runner changes

The release gate in SpecForge enforces this: a requirement must have
at least one verification artifact linked to it before the gate will
pass.

---

## Decisions and assumptions as first-class artifacts

Most projects make dozens of technical decisions during development.
Why was this database chosen? Why is the API structured this way? Why
does this module not handle X?

If these decisions are not recorded, they are re-litigated every time
someone new joins the team, or re-discovered the hard way when the
situation they addressed comes up again. "We tried that. Here's why
we didn't do it." is only useful if "here's why" was written down.

SpecForge records decisions as artifacts with a body that explains the
rationale, the alternatives considered, and the factors that drove the
choice. Decisions link to the requirements they support. If a
requirement changes, the impact on every linked decision is immediately
visible.

Assumptions are similar but different in character: a decision is a
choice that was made; an assumption is a belief about the world that
the project depends on. Assumptions should be reviewed periodically.
If an assumption is invalidated — the target platform changed, the
expected load is ten times higher — the requirements that depend on it
may need to be reconsidered. Recording assumptions is a risk management
practice.

Constraints are non-negotiable boundaries: legal requirements,
hardware limits, platform restrictions, organisational mandates. They
narrow the solution space before any design decision is made.
Documenting constraints prevents wasted effort exploring solutions that
cannot work.

---

## The release gate

A **release gate** is a formal check that must pass before software is
released. SpecForge's release gate requires two conditions:

1. **All approved requirements are verified.** Every requirement that
   is in the `approved` or later status must have verification evidence
   linked to it, and that evidence must be in `verified` status.

2. **No open tasks.** There are no tasks in `draft`, `proposed`, or
   `implemented` status that have not been resolved.

These conditions encode a simple principle: *you should not ship
something you have not verified, and you should not ship something
that has known unfinished work*.

The release gate is intentionally binary. This forces clarity. If the
gate fails, the reason is specific and actionable. If it passes, there
is documented evidence for every claim.

In CI pipelines, `specforge check ./project` exits with code 1 if the
gate fails and code 0 if it passes. This makes the gate automatable
without losing its meaning.
