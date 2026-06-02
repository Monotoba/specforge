from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from .models import ArtifactKind, ArtifactStatus
from .project import Project


class ExportFormat(StrEnum):
    CSV = "csv"
    MARKDOWN = "markdown"
    BOTH = "both"


def build_matrix(project: Project) -> list[dict[str, object]]:
    """One row per non-archived/non-rejected requirement with all forward links resolved."""
    artifacts = project.artifacts()

    tasks_by_req: dict[str, list[str]] = defaultdict(list)
    tests_by_req: dict[str, list[str]] = defaultdict(list)
    verifs_by_req: dict[str, list[str]] = defaultdict(list)
    decisions_by_req: dict[str, list[str]] = defaultdict(list)
    changes_by_req: dict[str, list[str]] = defaultdict(list)

    for a in artifacts:
        if a.kind == ArtifactKind.TASK:
            for req_id in a.implements:
                tasks_by_req[req_id].append(a.id)
        elif a.kind == ArtifactKind.TEST:
            for req_id in a.related_requirements:
                tests_by_req[req_id].append(a.id)
        elif a.kind == ArtifactKind.VERIFICATION:
            for req_id in a.related_requirements:
                verifs_by_req[req_id].append(a.id)
        elif a.kind == ArtifactKind.DECISION:
            for req_id in a.related_requirements:
                decisions_by_req[req_id].append(a.id)
        elif a.kind == ArtifactKind.CHANGE_ORDER:
            if a.source:
                changes_by_req[a.source].append(a.id)

    reqs = [
        a for a in artifacts
        if a.kind == ArtifactKind.REQUIREMENT
        and a.status not in (ArtifactStatus.ARCHIVED, ArtifactStatus.REJECTED)
    ]

    rows: list[dict[str, object]] = []
    for req in reqs:
        verifs = verifs_by_req.get(req.id, [])
        rows.append({
            "id": req.id,
            "title": req.title,
            "status": req.status.value,
            "tasks": tasks_by_req.get(req.id, []),
            "tests": tests_by_req.get(req.id, []),
            "verifications": verifs,
            "decisions": decisions_by_req.get(req.id, []),
            "change_orders": changes_by_req.get(req.id, []),
            "verified": bool(req.verified_by or verifs),
        })
    return rows


def to_csv(rows: list[dict[str, object]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "REQ_ID", "Title", "Status",
        "Tasks", "Tests", "Verifications", "Decisions", "Change_Orders", "Verified",
    ])
    for row in rows:
        writer.writerow([
            row["id"],
            row["title"],
            row["status"],
            " ".join(row["tasks"]),       # type: ignore[arg-type]
            " ".join(row["tests"]),       # type: ignore[arg-type]
            " ".join(row["verifications"]),  # type: ignore[arg-type]
            " ".join(row["decisions"]),   # type: ignore[arg-type]
            " ".join(row["change_orders"]),  # type: ignore[arg-type]
            "yes" if row["verified"] else "no",
        ])
    return out.getvalue()


def to_markdown(rows: list[dict[str, object]]) -> str:
    def _ids(row: dict[str, object], key: str) -> str:
        items = row[key]
        assert isinstance(items, list)
        return " ".join(items) if items else "—"

    lines = [
        "# Traceability Matrix",
        "",
        "| REQ ID | Title | Status | Tasks | Tests | Verifications | Decisions | Change Orders | Verified |",
        "|--------|-------|--------|-------|-------|---------------|-----------|---------------|----------|",
    ]
    for row in rows:
        check = "✓" if row["verified"] else "✗"
        lines.append(
            f"| {row['id']} | {row['title']} | {row['status']}"
            f" | {_ids(row, 'tasks')} | {_ids(row, 'tests')}"
            f" | {_ids(row, 'verifications')} | {_ids(row, 'decisions')}"
            f" | {_ids(row, 'change_orders')} | {check} |"
        )
    lines += [
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]
    return "\n".join(lines)


def export_project(project: Project, fmt: ExportFormat = ExportFormat.BOTH) -> dict[str, Path]:
    """Write matrix to trace/exports/. Returns {format: path} for each file written."""
    rows = build_matrix(project)
    exports_dir = project.root / "trace" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    written: dict[str, Path] = {}
    if fmt in (ExportFormat.CSV, ExportFormat.BOTH):
        p = exports_dir / f"traceability-{stamp}.csv"
        p.write_text(to_csv(rows), encoding="utf-8")
        written["csv"] = p
    if fmt in (ExportFormat.MARKDOWN, ExportFormat.BOTH):
        p = exports_dir / f"traceability-{stamp}.md"
        p.write_text(to_markdown(rows), encoding="utf-8")
        written["markdown"] = p
    return written
