from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.validation import validate_project


def test_validation_reports_missing_link(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF files",
        "The system shall export DXF files.",
        status=ArtifactStatus.APPROVED,
        depends_on=["REQ-9999"],
    )
    errors = validate_project(project)
    assert any("REQ-9999" in error for error in errors)
