from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project


def test_project_init_creates_memory_files(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    assert (project.root / "exploration" / "memory.md").exists()
    assert (project.root / "incubation" / "memory.md").exists()
    assert (project.root / "specification" / "memory.md").exists()


def test_create_requirement_round_trip(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF files",
        "The system shall export DXF files.",
        status=ArtifactStatus.APPROVED,
    )
    assert artifact.id == "REQ-0001"
    artifacts = project.artifacts()
    assert len(artifacts) == 1
    assert artifacts[0].title == "Export DXF files"
    assert artifacts[0].body == "The system shall export DXF files."
