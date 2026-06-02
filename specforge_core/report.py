from __future__ import annotations

from datetime import datetime, timezone

from .models import ArtifactKind, ArtifactStatus
from .project import Project
from .trace import TraceIndex


def build_acceptance_report(project: Project, index: TraceIndex) -> str:
    artifacts = project.artifacts()
    reqs = [
        a for a in artifacts
        if a.kind == ArtifactKind.REQUIREMENT
        and a.status not in (ArtifactStatus.ARCHIVED, ArtifactStatus.REJECTED)
    ]
    verified = [r for r in reqs if r.status == ArtifactStatus.VERIFIED or r.verified_by]
    unverified = index.unverified_requirements()
    open_tasks = [
        a for a in artifacts
        if a.kind == ArtifactKind.TASK
        and a.status not in (ArtifactStatus.VERIFIED, ArtifactStatus.ARCHIVED)
    ]
    change_orders = [a for a in artifacts if a.kind == ArtifactKind.CHANGE_ORDER]

    lines: list[str] = []
    project_name = project.config.project_name or str(project.root)
    lines.append(f"# SpecForge Acceptance Report — {project_name}")
    lines.append("")
    lines.append(f"Project: `{project.root}`")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    lines.append("## Requirements Coverage")
    lines.append("")
    lines.append(f"- Total requirements: {len(reqs)}")
    lines.append(f"- Verified: {len(verified)}")
    lines.append(f"- Unverified: {len(unverified)}")
    lines.append("")

    lines.append("| ID | Title | Status | Verified By |")
    lines.append("|----|-------|--------|-------------|")
    for r in reqs:
        verified_by = ", ".join(r.verified_by) if r.verified_by else "—"
        lines.append(f"| {r.id} | {r.title} | {r.status.value} | {verified_by} |")
    lines.append("")

    if unverified:
        lines.append("## Unverified Requirements")
        lines.append("")
        for row in unverified:
            lines.append(f"- **{row['id']}**: {row['title']} *(status: {row['status']})*")
        lines.append("")

    if open_tasks:
        lines.append("## Open Tasks")
        lines.append("")
        for task in open_tasks:
            impl = f" (implements: {', '.join(task.implements)})" if task.implements else ""
            lines.append(f"- **{task.id}**: {task.title} [{task.status.value}]{impl}")
        lines.append("")

    if change_orders:
        lines.append("## Change Orders")
        lines.append("")
        lines.append("| ID | Title | Status |")
        lines.append("|----|-------|--------|")
        for co in change_orders:
            lines.append(f"| {co.id} | {co.title} | {co.status.value} |")
        lines.append("")

    passed = len(unverified) == 0 and all(
        t.status in (ArtifactStatus.VERIFIED, ArtifactStatus.ARCHIVED) for t in open_tasks
    )
    lines.append("## Release Gate")
    lines.append("")
    lines.append(f"**{'PASS' if passed else 'FAIL'}** — "
                 + ("All requirements verified, no open tasks." if passed
                    else f"{len(unverified)} unverified requirement(s), {len(open_tasks)} open task(s)."))
    lines.append("")

    return "\n".join(lines)
