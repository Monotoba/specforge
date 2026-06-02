# User Guide

> For the full methodology guide, see [PROCESS.md](PROCESS.md).
> For core concepts, see [CONCEPTS.md](CONCEPTS.md).
> For CLI reference, see the built-in help: `specforge --help`.

---

## The five-phase process

SpecForge structures a project around five phases. These overlap in
practice — requirements are refined while implementation is underway,
and verification happens incrementally, not at the end.

### 1. Explore
Capture everything worth remembering as **idea** artifacts. Use
`specforge add-idea` freely. Record stakeholder conversations as
**conversation** artifacts. Tag ideas with version or sprint targets.
Use `specforge draft` to quickly turn rough notes into structured
artifacts.

### 2. Specify
Promote ideas to **candidates** when ready for evaluation, then to
**requirements** when approved. Write requirements that are unambiguous,
verifiable, and atomic. Record every non-obvious technical choice as a
**decision** with rationale. Document **assumptions** and **constraints**
before implementation begins.

### 3. Implement
Create **task** artifacts linked to requirements with `--implements`.
Mark tasks `implemented` as work is done. Use `specforge bulk` to
update many tasks at once at sprint boundaries.

### 4. Verify
Write **test** artifacts as specifications (what to test, how, expected
result). After testing, record **verification** artifacts with specific
evidence: build numbers, environment details, tester, measured values.
Mark requirements `verified` when evidence is recorded.

### 5. Release
Run `specforge check` to confirm the release gate passes. Generate the
acceptance report and traceability matrix. Archive completed artifacts.

---

## Key rules

**Discussion is not approval.** Requirements and change orders need
explicit status changes before they become binding project truth.

**Every task needs a requirement.** If a task cannot be linked to a
requirement with `--implements`, the requirement has not been written
yet. Write it.

**Record failures honestly.** A failing verification artifact is more
valuable than a missing one. It drives the investigation and provides
an audit trail.

**Use change orders for requirement changes.** Do not silently edit
an approved requirement. Create a change order, review it, then apply
the change and archive the order.

---

## Quick command reference

```bash
# Project
specforge init ./proj --git --name "Project Name"
specforge config ./proj --set git_commit=true

# Add artifacts
specforge add-idea ./proj "Title" "Body"
specforge add-req  ./proj "Title" --text "Body" --source CAND-0001
specforge add-task ./proj "Title" --text "Body" --implements REQ-0001
specforge add-test ./proj "Title" --text "Procedure" --req REQ-0001
specforge add-verification ./proj "Title" --text "Evidence" \
  --req REQ-0001 --test TEST-0001

# AI drafting
specforge draft ./proj requirement "Describe the requirement..."

# Status and links
specforge update-status ./proj TASK-0001 implemented
specforge link ./proj TASK-0001 --implements REQ-0002
specforge bulk ./proj archive --kind task --status implemented

# Review
specforge status ./proj         # health dashboard
specforge check ./proj          # release gate
specforge validate ./proj       # link integrity
specforge show ./proj REQ-0001  # show artifact with links

# Release
specforge report ./proj --output ACCEPTANCE_REPORT.md
specforge export ./proj         # traceability matrix
```

---

See also:
- [THEORY.md](THEORY.md) — why requirements management matters
- [PROCESS.md](PROCESS.md) — full methodology with examples
- [CONCEPTS.md](CONCEPTS.md) — definitions and explanations
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — extending SpecForge
- Tutorials: [REST API](tutorials/01_rest_api_spec.md) ·
  [Hardware](tutorials/02_hardware_bringup.md) ·
  [Agile](tutorials/03_sprint_planning.md)
