import pytest

from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project


def test_promote_idea_to_candidate(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF export", "Explore DXF export.")
    candidate = project.promote_artifact(idea.id, ArtifactKind.CANDIDATE)
    assert candidate.kind == ArtifactKind.CANDIDATE
    assert candidate.status == ArtifactStatus.PROPOSED
    assert candidate.source == idea.id
    assert candidate.title == idea.title


def test_promote_candidate_to_requirement(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF export", "Explore DXF.")
    cand = project.promote_artifact(idea.id, ArtifactKind.CANDIDATE)
    req = project.promote_artifact(cand.id, ArtifactKind.REQUIREMENT)
    assert req.kind == ArtifactKind.REQUIREMENT
    assert req.status == ArtifactStatus.APPROVED
    assert req.source == cand.id


def test_promote_requirement_to_task(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF",
        "The system shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    task = project.promote_artifact(req.id, ArtifactKind.TASK, implements=[req.id])
    assert task.kind == ArtifactKind.TASK
    assert task.status == ArtifactStatus.DRAFT
    assert req.id in task.implements


def test_update_status(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF",
        "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    updated = project.update_status(req.id, ArtifactStatus.IMPLEMENTED)
    assert updated.status == ArtifactStatus.IMPLEMENTED
    reloaded = project.get_artifact(req.id)
    assert reloaded.status == ArtifactStatus.IMPLEMENTED


def test_get_artifact_not_found(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    with pytest.raises(KeyError):
        project.get_artifact("REQ-9999")
