from specforge_core.contextpack import build_context_pack
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project


def test_context_pack_includes_approved_requirements(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF",
        "The system shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    pack = build_context_pack(project)
    ids = [r["id"] for r in pack["approved_requirements"]]  # type: ignore[index]
    assert req.id in ids


def test_context_pack_excludes_draft_requirements(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "Some idea", "Just exploring.")
    pack = build_context_pack(project)
    ids = [r["id"] for r in pack["approved_requirements"]]  # type: ignore[index]
    assert idea.id not in ids


def test_context_pack_open_tasks(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    task = project.create_artifact(ArtifactKind.TASK, "Implement DXF", "Build it.")
    pack = build_context_pack(project)
    task_ids = [t["id"] for t in pack["open_tasks"]]  # type: ignore[index]
    assert task.id in task_ids


def test_context_pack_unverified_requirements(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF",
        "The system shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    pack = build_context_pack(project)
    unverified_ids = [r["id"] for r in pack["unverified_requirements"]]  # type: ignore[index]
    assert req.id in unverified_ids


def test_context_pack_has_required_keys(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    pack = build_context_pack(project)
    for key in ("approved_requirements", "open_tasks", "decisions", "constraints",
                "unverified_requirements", "links", "artifact_count"):
        assert key in pack
