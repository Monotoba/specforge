# The SpecForge Development Process

This document describes the recommended methodology for using SpecForge
throughout a project lifecycle. It is written as a guide for teams who
want to adopt structured requirements management without heavyweight
process overhead.

SpecForge is not prescriptive. You can use as much or as little of this
methodology as suits your project. A solo developer on a weekend project
needs less ceremony than a team building a certified medical device. The
tooling supports everything from a single requirement file to hundreds
of linked artifacts; the process adapts accordingly.

---

## Phase overview

A SpecForge project moves through five phases:

```
1. EXPLORE      Capture everything worth remembering
2. SPECIFY      Formalise what must be built
3. IMPLEMENT    Build and track the work
4. VERIFY       Prove it was built correctly
5. RELEASE      Gate, report, archive
```

These phases overlap in practice. A real project is never a clean
waterfall. New ideas arrive during implementation. Requirements change
after verification begins. SpecForge is designed to accommodate this —
artifact statuses and links update incrementally as the project evolves.

---

## Phase 1: Explore

### Purpose
The exploration phase converts vague, implicit knowledge into explicit,
reviewable artifacts. At the start of a project, you know things that
are not written down: user pain points, technical possibilities,
constraints from past experience, assumptions about the target
environment. Exploration makes these visible.

### What you create

**Ideas** are the raw material of exploration. Write them freely and
quickly. An idea does not need to be complete, correct, or even viable
— it needs to exist as a record. Later decisions about what to pursue
and what to discard will be visible in the artifact history.

```bash
specforge add-idea ./proj "WebSocket real-time sync" \
  "Users on different devices should see changes within 500ms."

specforge add-idea ./proj "Offline-first architecture" \
  "Network reliability is poor in target environments. App must work offline."

specforge add-idea ./proj "Export to multiple formats" \
  "Sales have asked about PDF and CSV export. Unclear which is higher priority."
```

**Conversations** capture the context behind decisions: meeting notes,
stakeholder interviews, AI brainstorming sessions.

```bash
specforge add-conv ./proj "Stakeholder interview — Jane Smith" \
  --text "Primary pain point: data entry duplication across systems. 
  Would pay for automated sync. Not concerned about mobile."
```

**References** anchor exploration to primary sources: standards, papers,
competitor products, existing systems.

```bash
specforge add-ref ./proj "WebSocket RFC 6455" \
  --text "https://tools.ietf.org/html/rfc6455 — the wire protocol spec."
```

### When to promote

An idea is ready to become a **candidate** when:
- There is enough detail to evaluate feasibility
- At least one stakeholder has indicated interest or need
- It is specific enough to write acceptance criteria against

```bash
specforge promote ./proj IDEA-0001 candidate \
  --text "Confirmed with ops team: real-time sync is required for 
  collaborative editing. 500ms latency target comes from user research."
```

A candidate that is not promoted should be explicitly **rejected** with
a reason, not left in `draft` indefinitely.

```bash
specforge update-status ./proj IDEA-0003 rejected
specforge edit ./proj IDEA-0003  # Add rejection rationale to body
```

### Exploration patterns

**Don't filter too early.** The cost of recording an idea that turns out
to be wrong is low. The cost of not recording one that turns out to be
important is high. Write it down; decide later.

**Use AI drafting during exploration.** When you have a rough idea in
your head, `specforge draft` can turn it into a structured artifact in
seconds. Review and edit the result, but let AI handle the scaffolding.

```bash
specforge draft ./proj idea \
  "The import pipeline needs to handle malformed CSV gracefully" \
  --no-confirm
```

**Record disagreements.** When two stakeholders have conflicting
requirements, record both ideas and note the conflict in both bodies.
This makes the trade-off visible and forces an explicit resolution.

---

## Phase 2: Specify

### Purpose
The specification phase converts candidates into formal, verifiable
requirements with clear acceptance criteria. It also records the
decisions, assumptions, and constraints that bound the solution space.

This phase answers the question: *precisely what must the system do,
and under what conditions?*

### Writing good requirements

A well-formed requirement has four properties:

**Unambiguous**: there is exactly one interpretation. Vague words like
"fast", "user-friendly", "should", and "appropriate" make requirements
untestable. Replace them with specific, measurable criteria.

```
BAD:  The system should respond quickly.
GOOD: The system shall return search results within 200ms for queries
      against indexes of up to 1 million records, measured on hardware
      meeting the reference platform specification.
```

**Verifiable**: there exists a practical test that can determine whether
the requirement is satisfied. If you cannot write a test for it, the
requirement is either too vague or fundamentally untestable.

```
BAD:  The system shall be easy to use.
GOOD: A new user with no prior training shall complete the onboarding
      flow in under 5 minutes, as measured in usability testing with
      5 participants.
```

**Atomic**: the requirement expresses a single condition. Compound
requirements (those using "and" to join two separate conditions) should
be split — they may have different implementations, different tests, and
different priorities.

```
BAD:  The system shall export data as CSV and shall encrypt all exports.
GOOD: REQ-0010: The system shall export data in CSV format.
     REQ-0011: All data exports shall be encrypted with AES-256.
```

**Traceable**: the requirement links to its origin (an idea, a
stakeholder request, a regulatory obligation) via the `source` field.
This makes requirements auditable — you can always ask "why does this
exist?"

### Creating requirements

```bash
specforge add-req ./proj "Real-time sync within 500ms" \
  --text "The system shall propagate all document edits to connected 
  clients within 500 milliseconds, measured from the moment of edit 
  confirmation on the originating client to rendering on all other 
  connected clients, under a load of up to 100 simultaneous users." \
  --source CAND-0001 --git
```

### Decisions

For every requirement that involves a non-obvious technical choice,
record the decision and its rationale.

```bash
specforge add-decision ./proj "Use WebSocket for real-time sync" \
  --text "WebSocket (RFC 6455) was chosen over Server-Sent Events (SSE) 
  and long-polling because:
  1. Bidirectional: client edits need to travel server→client AND 
     client→server without separate HTTP requests.
  2. Lower overhead: WebSocket frames have a 2-14 byte header vs 
     HTTP's ~500 byte minimum header.
  3. Mature tooling: browser support is universal; server libraries 
     exist for all major languages.
  
  SSE was rejected because it is unidirectional (server to client only).
  Long-polling was rejected because it cannot meet the 500ms latency 
  target at scale.
  
  Risk: WebSockets are blocked by some enterprise proxies. Mitigation: 
  fall back to long-polling when WebSocket connection fails." \
  --req REQ-0001 --git
```

The body of a decision should always explain the **alternatives
considered and the reasons they were rejected**. A decision that records
only what was chosen, without explaining why, is of limited value.

### Assumptions

Record any belief about the operating environment that the system
depends on.

```bash
specforge add-assumption ./proj "Node.js 20+ on all server hosts" \
  --text "The deployment specification requires Node.js 20 LTS or 
  later. The WebSocket library requires Node.js 18+. This assumption 
  will be validated in the deployment checklist." \
  --req REQ-0001
```

### Constraints

Record any non-negotiable boundary before design work begins.

```bash
specforge add-constraint ./proj "No third-party cloud dependencies" \
  --text "All system components must be self-hostable. No reliance on 
  third-party cloud services (AWS, GCP, Azure, Cloudflare) as primary 
  infrastructure. This is a contractual requirement from the customer." \
  --req REQ-0001
```

### Change orders

When a requirement needs to change after it has been approved, do not
simply edit it. Create a change order that documents what is changing,
why, and what the impact is.

```bash
specforge add-co ./proj "Increase sync latency target to 1000ms" \
  --text "The 500ms target was set without load testing data. Initial 
  performance profiling shows 500ms is not achievable at 100 users 
  with our current architecture without a significant infrastructure 
  investment. Proposing relaxing to 1000ms, which is achievable with 
  the current design and within acceptable UX tolerance (Nielsen 1993: 
  1 second is the limit for flow of thought)." --git
```

The change order enters a review cycle. When approved, update the
original requirement and archive the change order.

### Specification review checklist

Before leaving the specification phase, confirm:

- [ ] Every candidate has been either promoted to a requirement or rejected
- [ ] Every requirement is unambiguous, verifiable, and atomic
- [ ] Every requirement that involves a technical choice has a linked decision
- [ ] Every assumption is recorded and assigned an owner for review
- [ ] Every constraint is documented
- [ ] `specforge validate ./proj` passes (no broken links)
- [ ] `specforge status ./proj` shows release gate status (likely FAIL at this stage — that is expected)

---

## Phase 3: Implement

### Purpose
The implementation phase tracks the work of building the system. Tasks
are the primary artifact. Each task should implement one or more
requirements, and should be specific enough to be assigned, estimated,
and completed by a single person in a short time.

### Creating tasks

```bash
specforge add-task ./proj "Implement WebSocket server handler" \
  --text "Build the server-side WebSocket handler that:
  - Accepts connections at /ws with JWT authentication
  - Broadcasts document edit events to all connected clients in the 
    same document session
  - Handles disconnections gracefully with session cleanup
  - Tracks connection count per session for load monitoring
  
  Exit criteria: handler passes the WebSocket load test at 100 
  simultaneous connections." \
  --implements REQ-0001 --git

specforge add-task ./proj "Implement WebSocket client library" \
  --text "Build the client-side WebSocket wrapper that:
  - Connects on document open, disconnects on document close
  - Applies incoming edits using OT (operational transform)
  - Falls back to long-polling when WebSocket is unavailable
  - Exposes a connection status indicator to the UI layer" \
  --implements REQ-0001 --depends-on TASK-0001 --git
```

### Task granularity

Tasks should be sized so that a single person can complete them in
one to a few days. Tasks that are too large hide progress and make
estimation difficult. If a task cannot be described in a single,
coherent paragraph, it is probably too large.

Conversely, tasks that are too small (hours of work) create overhead
without adding clarity. A task like "write unit test for connection
handler" is usually better captured as part of the connection handler
task's exit criteria than as a separate artifact.

### Managing progress

Update task status as work proceeds:

```bash
# Task is ready to start
specforge update-status ./proj TASK-0001 proposed

# Work is complete
specforge update-status ./proj TASK-0001 implemented --git
```

When all tasks implementing a requirement are `implemented`, update
the requirement:

```bash
specforge update-status ./proj REQ-0001 implemented
```

### Using bulk operations

At sprint boundaries, update many artifacts at once:

```bash
# See what would be archived before doing it
specforge bulk ./proj archive \
  --kind task --status implemented --dry-run

# Archive all implemented tasks in one command
specforge bulk ./proj archive \
  --kind task --status implemented

# Tag all new sprint-13 tasks
specforge bulk ./proj tag-add \
  --kind task --status draft --add-tag sprint-13
```

### Implementation anti-patterns

**The orphaned task**: a task with no `implements` link. If a task does
not implement a requirement, ask why it exists. Either link it to a
requirement you have not written yet (write the requirement), or
acknowledge that it is technical debt or infrastructure work by tagging
it accordingly.

**The mega-task**: a task whose body spans multiple screens. These
invariably contain multiple distinct pieces of work that should be
tracked separately.

**The silent status change**: updating a requirement to `implemented`
before all its linked tasks are done. Status should reflect reality.
If REQ-0001 has three tasks and only one is done, the requirement is
not implemented.

---

## Phase 4: Verify

### Purpose
The verification phase creates the documented evidence that the system
satisfies its requirements. This is different from testing — testing is
an activity; verification is a conclusion supported by evidence.

### Writing test specifications

Write test artifacts during or immediately after specification, while
the requirements are still being written. This is the practice of
**acceptance test-driven development**: you define what you will test
before you write the code that will be tested.

```bash
specforge add-test ./proj "WebSocket 500ms latency test" \
  --text "
## Objective
Verify that REQ-0001 is satisfied: document edits propagate to 
connected clients within 500ms under load.

## Environment
- Server: reference platform (4 vCPU, 8 GB RAM)
- Clients: 100 simultaneous WebSocket connections
- Document: 10KB working document with collaborative editing

## Procedure
1. Start the server with production configuration
2. Open 100 WebSocket connections using the load test harness
3. From client 1: apply a text edit to the document
4. Measure time from server receipt to last client rendering

## Expected result
- p50 latency < 200ms
- p95 latency < 500ms
- p99 latency < 1000ms
- No connection drops during the 5-minute test run

## Tooling
ws-load-test harness (tools/load_test/ws_latency.py)" \
  --req REQ-0001 --git
```

Note the structure: objective, environment, procedure, expected result.
This makes the test reproducible by anyone — not just the person who
wrote it.

### Recording verification evidence

After running a test:

```bash
specforge add-verification ./proj "WebSocket latency — CI green" \
  --text "
## Result: PASS

Run date:    2026-06-02
Environment: CI runner (4 vCPU, 8 GB, Ubuntu 22.04)
Build:       #342 (main branch, commit a8d851f)
Tester:      CI pipeline / Randy Morgan

## Measurements
p50: 87ms  ✓ (< 200ms)
p95: 312ms ✓ (< 500ms)
p99: 498ms ✓ (< 1000ms)
Connections: 100/100 sustained for 5 minutes, 0 drops ✓

## Attachments
Full latency histogram: artifacts/ws_latency_build342.png
Load test log: artifacts/ws_load_build342.log" \
  --req REQ-0001 --test TEST-0001 --git

specforge update-status ./proj REQ-0001 verified --git
```

### Evidence standards

Good verification evidence is:

**Specific**: it names the exact build, date, environment, and result.
"Tests passed" is not evidence. "Build #342 on Ubuntu 22.04, 100% pass
rate, p95 latency 312ms, log available at CI URL" is evidence.

**Reproducible**: the procedure is clear enough that someone else could
repeat the test and expect the same result.

**Honest**: record failures and partial passes accurately. A
verification artifact that records a failure is more valuable than one
that misrepresents a pass — it drives the investigation and fix that
follow.

**Linked**: the verification artifact links to the requirement it
satisfies and the test specification it follows.

### Handling test failures

When a test fails:

1. Record the failure honestly in a verification artifact
2. Create a task to investigate and fix the defect
3. Link the task to the failed requirement
4. Re-run the test after the fix
5. Create a new, passing verification artifact
6. Update the requirement to `verified`

The failing verification artifact should not be deleted — it is part
of the project history and shows the investigation trail.

---

## Phase 5: Release

### Purpose
The release phase confirms that all requirements have been verified,
generates the formal release artefacts, and prepares the project for
archival.

### Release gate check

```bash
specforge check ./proj
```

This command exits 0 (success) if and only if:
- All approved/implemented requirements are in `verified` status
- There are no open tasks (draft, proposed, or implemented)

If the gate fails, the output shows exactly which requirements are
unverified and which tasks are open. There is no ambiguity about what
must be done before release.

**The gate is intentionally strict.** If a requirement was descoped,
move it to `rejected` or `archived` so the gate sees a clean project.
If a task is deferred to a future sprint, archive it or tag it for
the next sprint and move it out of the current scope.

### Generating release artefacts

```bash
# Formal acceptance report
specforge report ./proj \
  --output ./proj/ACCEPTANCE_REPORT.md

# Traceability matrix (CSV and Markdown)
specforge export ./proj

# AI context pack (for post-project handover or future AI sessions)
specforge context-pack ./proj \
  --output ./proj/CONTEXT_PACK.json
```

### The acceptance report

The acceptance report is a structured Markdown document that:
- States the project name and release date
- Shows the release gate result (PASS/FAIL)
- Lists every requirement with its status and linked verifications
- Lists all unverified requirements (if any)
- Provides a summary count by artifact kind

This document is suitable for human review, customer sign-off, and
regulatory submission. It provides a permanent, auditable record of
what was built and how it was verified.

### The traceability matrix

The traceability matrix export produces a table linking every
requirement to its implementing tasks and its verification evidence.
This is the standard output required by certification processes
(ISO 26262, IEC 62443, DO-178C, FDA 21 CFR Part 11, etc.).

```bash
specforge export ./proj --format csv       # machine-readable
specforge export ./proj --format markdown  # human-readable
specforge export ./proj --format both      # both
```

### Archival

After release, archive completed artifacts and tag the project state:

```bash
# Archive all verified requirements
specforge bulk ./proj archive \
  --kind requirement --status verified

# Tag the release state
specforge bulk ./proj tag-add \
  --tag release-1.0

# Git tag
git -C ./proj tag -a v1.0 -m "Release 1.0 — all requirements verified"
```

---

## Continuous use: iterative development

SpecForge works equally well with iterative (agile) development. The
phases described above happen within each iteration, not once per
project.

### Sprint planning with SpecForge

1. **Backlog refinement**: create or promote candidates to requirements
   for the upcoming sprint. Tag them with the sprint name.

```bash
specforge bulk ./proj tag-add \
  --kind requirement --status approved \
  --tag sprint-13
```

2. **Task creation**: create tasks implementing each sprint requirement.
   Use AI drafting to speed up task body writing.

```bash
specforge draft ./proj task \
  "Implement the WebSocket fallback to long-polling when WS is blocked by proxy" \
  --title "WS fallback implementation" \
  --tag sprint-13
```

3. **Sprint execution**: update task statuses as work proceeds.

4. **Sprint review**: run the release gate on sprint requirements:

```bash
specforge check ./proj
specforge status ./proj
```

5. **Sprint close**: archive done tasks, move incomplete items to the
   next sprint:

```bash
specforge bulk ./proj archive \
  --kind task --status implemented --tag sprint-13

specforge bulk ./proj tag-add \
  --kind task --status draft --tag sprint-13 \
  --add-tag sprint-13-deferred
```

### Living requirements

Requirements change. This is normal. SpecForge's process for handling
requirement changes:

1. Create a **change order** documenting the proposed change and its
   rationale
2. Review the change order with stakeholders
3. If approved: update the requirement body, reset status to `approved`,
   create new tasks, and archive the change order
4. If rejected: archive the change order with the rejection rationale

This process maintains a complete audit trail. The original requirement
and the change request are both preserved. Anyone can see that the
requirement was different at version 1.0 and understand why it changed.

---

## Process anti-patterns

**The Big Upfront Spec**: writing exhaustive requirements for every
feature before any implementation begins, treating SpecForge as a
heavyweight documentation tool. This defeats the purpose. Use
exploration artifacts to capture uncertainty early; refine requirements
iteratively.

**Requirements as tasks**: writing requirements that describe
implementation steps ("the system shall call the API with a POST
request") rather than system behaviour ("the system shall save user
preferences"). Requirements describe the *what*, not the *how*.

**Unlinked tasks**: tasks created without `--implements` links. Every
task should be traceable to a requirement. If it can't be, the
requirement hasn't been written yet.

**Skipping verification artifacts**: marking requirements `verified`
without creating verification evidence. The verification artifact is
not bureaucracy — it is the answer to "how do we know this works?" in
six months.

**Keeping failed verifications secret**: recording only passing tests.
Failed verification artifacts are valuable — they document the
investigation, drive the fix, and provide a complete picture of the
quality journey.

**Stale ideas**: letting dozens of ideas accumulate in `draft` status
indefinitely. Ideas should be either promoted, rejected, or archived
within a reasonable time. An inbox that is never emptied provides no
signal.

---

## Working with AI tools

SpecForge is designed for human-AI collaboration. The AI plays three
distinct roles:

### AI as drafter
Use `specforge draft` to generate artifact bodies from plain-language
descriptions. AI drafting is most effective for:
- Requirements bodies (turning a one-line description into a
  well-formed, verifiable requirement)
- Decision rationales (prompting a structured analysis of options)
- Test specifications (generating a complete test procedure from a
  description of what to test)

Always review AI-generated content. The AI produces a starting point,
not a finished artifact. Verify that generated requirements are
unambiguous, that generated tests are actually executable, and that
generated decisions accurately reflect your context.

### AI as reviewer
Share a `specforge context-pack` output with your AI assistant and ask
it to review the requirements for completeness, ambiguity, and
consistency. This is a quick sanity check that catches obvious problems
before implementation begins.

```bash
specforge context-pack ./proj --output context.json
# Attach context.json to a Claude conversation and ask:
# "Review these requirements for clarity, completeness, and consistency."
```

### AI as agent (MCP integration)
With the MCP server configured, Claude Code can read and write
artifacts directly during development. Claude can:
- Look up the requirement a piece of code is implementing
- Create a task when it discovers missing work
- Check the release gate status
- Find related decisions when making a design choice

This closes the loop between the requirements system and the
development environment. See **MCP / Claude Code** in the help system
for setup instructions.
