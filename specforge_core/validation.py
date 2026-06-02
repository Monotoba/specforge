from __future__ import annotations

from .models import ArtifactKind, ArtifactStatus
from .project import Project


def validate_project(project: Project) -> list[str]:
    errors: list[str] = []
    artifacts = project.artifacts()
    ids = {artifact.id for artifact in artifacts}
    for artifact in artifacts:
        for field in [
            "depends_on",
            "dependents",
            "related_requirements",
            "related_decisions",
            "related_assumptions",
            "references",
            "verified_by",
            "implements",
        ]:
            for linked_id in getattr(artifact, field):
                if linked_id not in ids:
                    errors.append(f"{artifact.id}: {field} references missing artifact {linked_id}")
        if artifact.source and artifact.source not in ids:
            errors.append(f"{artifact.id}: source references missing artifact {artifact.source}")
        if artifact.kind == ArtifactKind.REQUIREMENT and artifact.status == ArtifactStatus.APPROVED:
            if not artifact.body.strip():
                errors.append(f"{artifact.id}: approved requirement has empty body")
    return errors
