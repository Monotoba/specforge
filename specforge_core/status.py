from __future__ import annotations

from collections import Counter

from .models import ArtifactKind, ArtifactStatus
from .project import Project
from .trace import TraceIndex


def project_status(project: Project) -> dict[str, object]:
    """Return a structured summary of project health."""
    artifacts = project.artifacts()

    # Per-kind counts
    kind_counts: dict[str, int] = Counter(a.kind.value for a in artifacts)

    # Per-kind, per-status breakdown (only non-zero)
    breakdown: dict[str, dict[str, int]] = {}
    for a in artifacts:
        breakdown.setdefault(a.kind.value, Counter())[a.status.value] += 1  # type: ignore[index]

    # Open tasks (not verified / not archived)
    open_tasks = [
        {"id": a.id, "title": a.title, "status": a.status.value}
        for a in artifacts
        if a.kind == ArtifactKind.TASK
        and a.status not in (ArtifactStatus.VERIFIED, ArtifactStatus.ARCHIVED)
    ]

    # Unverified approved/implemented requirements
    index = TraceIndex(project)
    if not index.db_path.exists():
        index.rebuild()
    unverified = index.unverified_requirements()

    passed = len(unverified) == 0 and len(open_tasks) == 0

    return {
        "project_root": str(project.root),
        "project_name": project.config.project_name,
        "total_artifacts": len(artifacts),
        "kind_counts": dict(kind_counts),
        "breakdown": {k: dict(v) for k, v in breakdown.items()},
        "open_tasks": open_tasks,
        "unverified_requirements": unverified,
        "gate": "PASS" if passed else "FAIL",
    }
