from __future__ import annotations

from .models import ArtifactKind, ArtifactStatus
from .project import Project
from .trace import TraceIndex


def build_context_pack(project: Project) -> dict[str, object]:
    artifacts = project.artifacts()
    ids = {a.id for a in artifacts}

    approved_reqs = [
        _artifact_dict(a)
        for a in artifacts
        if a.kind == ArtifactKind.REQUIREMENT
        and a.status in (ArtifactStatus.APPROVED, ArtifactStatus.IMPLEMENTED, ArtifactStatus.VERIFIED)
    ]

    open_tasks = [
        _artifact_dict(a)
        for a in artifacts
        if a.kind == ArtifactKind.TASK
        and a.status not in (ArtifactStatus.ARCHIVED, ArtifactStatus.VERIFIED)
    ]

    decisions = [
        _artifact_dict(a)
        for a in artifacts
        if a.kind == ArtifactKind.DECISION
        and a.status not in (ArtifactStatus.ARCHIVED, ArtifactStatus.REJECTED)
    ]

    constraints = [
        _artifact_dict(a)
        for a in artifacts
        if a.kind == ArtifactKind.CONSTRAINT
        and a.status not in (ArtifactStatus.ARCHIVED, ArtifactStatus.REJECTED)
    ]

    index = TraceIndex(project)
    if not index.db_path.exists():
        index.rebuild()
    unverified = index.unverified_requirements()

    links: list[dict[str, str]] = []
    for a in artifacts:
        for field in (
            "depends_on",
            "dependents",
            "related_requirements",
            "related_decisions",
            "related_assumptions",
            "references",
            "verified_by",
            "implements",
        ):
            for dst in getattr(a, field):
                if dst in ids:
                    links.append({"src": a.id, "dst": dst, "type": field})
        if a.source and a.source in ids:
            links.append({"src": a.id, "dst": a.source, "type": "source"})

    return {
        "project_root": str(project.root),
        "approved_requirements": approved_reqs,
        "open_tasks": open_tasks,
        "decisions": decisions,
        "constraints": constraints,
        "unverified_requirements": unverified,
        "links": links,
        "artifact_count": len(artifacts),
    }


def _artifact_dict(a: object) -> dict[str, object]:
    from .models import Artifact

    assert isinstance(a, Artifact)
    return {
        "id": a.id,
        "kind": a.kind.value,
        "title": a.title,
        "status": a.status.value,
        "body": a.body,
        "source": a.source,
        "depends_on": a.depends_on,
        "implements": a.implements,
        "verified_by": a.verified_by,
        "tags": a.tags,
    }
