#!/usr/bin/env bash
# SpecForge demo project — walks the full artifact lifecycle end to end.
# Usage: ./scripts/create_demo_project.sh [output-dir]
set -euo pipefail

PROJECT=${1:-examples/demo_project}

# Wipe any previous run so the script is idempotent
rm -rf "$PROJECT"

step() { echo; echo "─────────────────────────────────────────"; echo "  $*"; echo "─────────────────────────────────────────"; }

# ── 1. Initialise ────────────────────────────────────────────────────────────
step "1. Init project (git-tracked, with project name)"
specforge init "$PROJECT" --git --name "Drawing Export System"

step "1b. Configure: auto-commit all writes"
specforge config "$PROJECT" --set git_commit=true

# ── 2. Exploration ───────────────────────────────────────────────────────────
step "2. Capture exploration ideas"
specforge add-idea "$PROJECT" "DXF export" \
  "Users need to export drawings as DXF files for CAD tool interoperability." \
  --tag v1.0 --tag export

specforge add-idea "$PROJECT" "SVG export" \
  "Web-friendly vector format for embedded previews and dashboards." \
  --tag v2.0 --tag export

specforge add-idea "$PROJECT" "Batch processing" \
  "Process multiple files in a single command to support CI pipelines." \
  --tag v1.0

# ── 3. Incubation ─────────────────────────────────────────────────────────────
step "3. Promote ideas to candidates"
specforge promote "$PROJECT" IDEA-0001 candidate \
  --text "DXF export is mature enough to specify. CAD interop is a top user ask." --git

specforge promote "$PROJECT" IDEA-0003 candidate \
  --text "Batch mode enables CI/CD automation. Clear implementation path via glob input."

# ── 4. Requirements ──────────────────────────────────────────────────────────
step "4. Approve requirements"
specforge add-req "$PROJECT" "Export DXF files" \
  --text "The system shall export project drawings as DXF files compatible with AutoCAD 2018+." \
  --source CAND-0001 --git

specforge add-req "$PROJECT" "Batch export" \
  --text "The system shall accept a glob pattern and export all matching files in a single invocation." \
  --source CAND-0002 --git

specforge add-req "$PROJECT" "Configurable output directory" \
  --text "The system shall write output files to a user-specified directory, defaulting to the source directory." \
  --git

# ── 5. Decisions, assumptions, constraints ───────────────────────────────────
step "5. Record decisions, assumptions, and constraints"
specforge add-decision "$PROJECT" "Use ezdxf library" \
  --text "ezdxf is the most actively maintained Python DXF library (11k GitHub stars, regular releases). Alternatives (dxfgrabber, sdxf) are unmaintained." \
  --req REQ-0001 --git

specforge add-assumption "$PROJECT" "Python 3.11+ available on target hosts" \
  --text "All deployment targets run Python 3.11 or newer. This is verified by the CI matrix." \
  --req REQ-0001 --req REQ-0002

specforge add-constraint "$PROJECT" "Output must be offline-capable" \
  --text "No external network calls during export. All processing runs locally." \
  --req REQ-0001

# ── 6. Change order ──────────────────────────────────────────────────────────
step "6. Propose a change order"
specforge add-co "$PROJECT" "Add PDF sidecar output" \
  --text "Proposed: alongside each DXF, emit a PDF preview. Affects REQ-0001 scope and timeline." --git

# ── 7. Tasks ─────────────────────────────────────────────────────────────────
step "7. Create development tasks"
specforge add-task "$PROJECT" "Implement DXF exporter" \
  --text "Build the ezdxf-based export module. Accept a Project object and output path." \
  --implements REQ-0001 --git

specforge add-task "$PROJECT" "Implement batch glob runner" \
  --text "Add CLI argument parsing for glob input. Call the exporter for each matched file." \
  --implements REQ-0002 --depends-on TASK-0001 --git

specforge add-task "$PROJECT" "Add --output-dir flag" \
  --text "Wire --output-dir into the CLI. Default to source directory when not specified." \
  --implements REQ-0003 --depends-on TASK-0001

# ── 8. Mark tasks implemented, update requirement statuses ───────────────────
step "8. Mark tasks implemented"
specforge update-status "$PROJECT" TASK-0001 implemented --git
specforge update-status "$PROJECT" TASK-0002 implemented --git
specforge update-status "$PROJECT" TASK-0003 implemented

specforge update-status "$PROJECT" REQ-0001 implemented --git
specforge update-status "$PROJECT" REQ-0002 implemented
specforge update-status "$PROJECT" REQ-0003 implemented

# ── 9. Tests ─────────────────────────────────────────────────────────────────
step "9. Define tests"
specforge add-test "$PROJECT" "DXF round-trip test" \
  --text "Load a sample drawing, export to DXF, re-import with ezdxf, assert entity count matches." \
  --req REQ-0001 --git

specforge add-test "$PROJECT" "Batch export test" \
  --text "Run exporter against a directory of 10 sample files. Assert 10 DXF outputs are produced." \
  --req REQ-0002 --git

specforge add-test "$PROJECT" "Output directory test" \
  --text "Export to a custom --output-dir. Assert files land in the correct directory, not the source directory." \
  --req REQ-0003

# ── 10. Verification evidence ────────────────────────────────────────────────
step "10. Record verification evidence"
specforge add-verification "$PROJECT" "DXF export verified — CI green" \
  --text "All three tests passed on CI (Ubuntu 22.04, Python 3.12). Build #147. No regressions." \
  --req REQ-0001 --test TEST-0001 --git

specforge add-verification "$PROJECT" "Batch and output-dir verified — CI green" \
  --text "Batch and output-dir tests passed on CI. Build #147." \
  --req REQ-0002 --req REQ-0003 --test TEST-0002 --test TEST-0003

# ── 11. Mark requirements verified ───────────────────────────────────────────
step "11. Mark requirements verified"
specforge update-status "$PROJECT" REQ-0001 verified --git
specforge update-status "$PROJECT" REQ-0002 verified
specforge update-status "$PROJECT" REQ-0003 verified

# ── 12. Archive completed tasks ──────────────────────────────────────────────
step "12. Archive completed tasks"
specforge update-status "$PROJECT" TASK-0001 archived --git
specforge update-status "$PROJECT" TASK-0002 archived
specforge update-status "$PROJECT" TASK-0003 archived

# ── 13. Rebuild trace index ───────────────────────────────────────────────────
step "13. Rebuild trace index"
specforge trace "$PROJECT"

# ── 14. Validate ─────────────────────────────────────────────────────────────
step "14. Validate project"
specforge validate "$PROJECT"

# ── 15. Search ───────────────────────────────────────────────────────────────
step "15. Search: 'DXF export'"
specforge search "$PROJECT" "DXF export"

step "15b. Search filtered to requirements only"
specforge search "$PROJECT" "export" --kind requirement

# ── 16. Project status dashboard ────────────────────────────────────────────
step "16. Project status dashboard"
specforge status "$PROJECT"

# ── 16b. Show artifact with resolved links ───────────────────────────────────
step "16b. Show artifact with resolved links"
specforge show "$PROJECT" TASK-0001

# ── 16c. CI gate check (all requirements verified, no open tasks) ────────────
step "16c. CI gate check"
specforge check "$PROJECT"

# ── 17. Acceptance report ────────────────────────────────────────────────────
step "17. Acceptance report"
specforge report "$PROJECT" --output "$PROJECT/ACCEPTANCE_REPORT.md"
echo "Report written. Gate status:"
grep "Release Gate" -A2 "$PROJECT/ACCEPTANCE_REPORT.md"

# ── 18. Traceability matrix export ───────────────────────────────────────────
step "18. Traceability matrix export"
specforge export "$PROJECT"

# ── 19. Search by tag ───────────────────────────────────────────────────────
step "19. Search by tag (v1.0 features)"
specforge search "$PROJECT" "" --tag v1.0

# ── 20. AI context pack ──────────────────────────────────────────────────────
step "20. AI context pack"
specforge context-pack "$PROJECT" --output "$PROJECT/context_pack.json"
echo "Context pack artifact counts:"
python3 -c "
import json, pathlib
pack = json.loads(pathlib.Path('$PROJECT/context_pack.json').read_text())
print(f\"  approved_requirements : {len(pack['approved_requirements'])}\")
print(f\"  open_tasks            : {len(pack['open_tasks'])}\")
print(f\"  unverified            : {len(pack['unverified_requirements'])}\")
print(f\"  total artifacts       : {pack['artifact_count']}\")
"

# ── 21. Git log ───────────────────────────────────────────────────────────────
step "21. Git log (artifact commits)"
specforge log "$PROJECT"

# ── 22. Summary ──────────────────────────────────────────────────────────────
step "Done — demo project at: $PROJECT"
specforge list "$PROJECT"
