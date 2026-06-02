from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.report import build_acceptance_report
from specforge_core.trace import TraceIndex


def test_report_shows_unverified_requirements(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF",
        "The system shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    index = TraceIndex(project)
    index.rebuild()
    report = build_acceptance_report(project, index)
    assert req.id in report
    assert "Unverified Requirements" in report
    assert "FAIL" in report


def test_report_passes_when_all_verified(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    test_art = project.create_artifact(ArtifactKind.TEST, "DXF test", "Test DXF export.")
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT,
        "Export DXF",
        "The system shall export DXF.",
        status=ArtifactStatus.VERIFIED,
        verified_by=[test_art.id],
    )
    index = TraceIndex(project)
    index.rebuild()
    report = build_acceptance_report(project, index)
    assert req.id in report
    assert "PASS" in report


def test_report_includes_change_orders(tmp_path):
    project = Project(tmp_path / "demo")
    project.init()
    project.create_artifact(ArtifactKind.CHANGE_ORDER, "Add PDF export", "Export PDF too.")
    index = TraceIndex(project)
    index.rebuild()
    report = build_acceptance_report(project, index)
    assert "Change Orders" in report
