# Workflow Guide

SpecForge is built around a single idea: every piece of work should be
traceable from the original intent (idea) through the formal requirement,
the implementation task, and the test evidence that proves it works.

---

## The core loop

```
Explore → Specify → Implement → Verify → Release
```

### 1. Explore

Start with ideas — raw notes, user feedback, design sketches.

```bash
specforge add-idea ./proj "Offline support" \
  "Users lose work when the network drops."
```

Promote promising ideas to candidates when they have enough detail to
evaluate:

```bash
specforge promote ./proj IDEA-0001 candidate \
  --text "Confirmed demand from 12 support tickets. Technically feasible with SQLite cache."
```

### 2. Specify

Write a formal requirement when a candidate is approved.

```bash
specforge add-req ./proj "Offline read access" \
  --text "The app shall serve cached content when no network connection is available." \
  --source CAND-0001 --git
```

Capture the reasoning as a decision:

```bash
specforge add-decision ./proj "Use SQLite for offline cache" \
  --text "SQLite is available on all platforms without additional dependencies." \
  --req REQ-0001 --git
```

### 3. Implement

Create tasks linked to requirements:

```bash
specforge add-task ./proj "Build offline cache layer" \
  --text "Implement SQLite-backed cache. Read from cache on network failure." \
  --implements REQ-0001 --git
```

Mark tasks done as work is completed:

```bash
specforge update-status ./proj TASK-0001 implemented --git
specforge update-status ./proj REQ-0001 implemented
```

### 4. Verify

Write a test specification:

```bash
specforge add-test ./proj "Offline cache test" \
  --text "Disable network. Open app. Assert cached feed loads within 2 s." \
  --req REQ-0001
```

Record the evidence after testing:

```bash
specforge add-verification ./proj "Offline cache — QA passed" \
  --text "Tested on iOS 17 and Android 14. All scenarios passed. No data loss." \
  --req REQ-0001 --test TEST-0001 --git
```

Mark the requirement verified:

```bash
specforge update-status ./proj REQ-0001 verified --git
```

### 5. Release

Check the release gate — all requirements verified, no open tasks:

```bash
specforge check ./proj     # exits 0 on PASS, 1 on FAIL
```

Generate the acceptance report and traceability matrix:

```bash
specforge report ./proj --output ./proj/ACCEPTANCE_REPORT.md
specforge export ./proj
```

---

## Bulk operations for sprint close

At the end of a sprint, batch-update multiple artifacts at once:

```bash
# Archive all implemented tasks
specforge bulk ./proj archive --kind task --status implemented

# Tag all new items for the next sprint
specforge bulk ./proj tag-add --kind requirement --status approved \
  --add-tag sprint-13

# Dry-run to preview before writing
specforge bulk ./proj update-status --kind task --status draft \
  --to proposed --dry-run
```

---

## Using AI to speed up drafting

Generate artifact bodies from a free-form prompt:

```bash
specforge draft ./proj requirement \
  "Passwords must be at least 12 characters and contain a symbol" \
  --title "Password complexity policy" --git
```

SpecForge calls your configured LLM, shows the generated body, and
asks for confirmation. See **AI Drafting** in the Help menu for
provider setup.

---

## Traceability and validation

View the full link graph for any artifact:

```bash
specforge graph ./proj REQ-0001
```

Run validation to find broken links or status inconsistencies:

```bash
specforge validate ./proj
```

Rebuild the SQLite trace index at any time (safe to run often):

```bash
specforge trace ./proj
```

---

## Project health dashboard

```bash
specforge status ./proj
```

Shows:
- Artifact counts by kind
- Status breakdown per kind
- Open tasks (blocking release)
- Unverified requirements (blocking release)
- Release gate: PASS / FAIL

---

## Git integration

Any command accepts `--git` to commit that artifact automatically.
Or set `git_commit: true` in `.specforge.yaml` to commit everything
by default:

```bash
specforge config ./proj --set git_commit=true
```

The traceability SQLite database is excluded from git (it is listed
in `.gitignore` automatically). All other artifacts are plain Markdown
files and commit cleanly.
