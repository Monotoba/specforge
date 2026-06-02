from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.export import (
    ExportFormat,
    build_matrix,
    export_project,
    to_csv,
    to_markdown,
)
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project

runner = CliRunner()


def _setup_project(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    task = project.create_artifact(
        ArtifactKind.TASK, "Build DXF exporter", "Implement it.", implements=[req.id],
    )
    test = project.create_artifact(
        ArtifactKind.TEST, "DXF test", "Verify export.", related_requirements=[req.id],
    )
    ver = project.create_artifact(
        ArtifactKind.VERIFICATION, "DXF verified", "All passed.",
        related_requirements=[req.id], verified_by=[test.id],
    )
    dec = project.create_artifact(
        ArtifactKind.DECISION, "Use ezdxf", "Best library.",
        related_requirements=[req.id],
    )
    return project, req, task, test, ver, dec


def test_build_matrix_row_structure(tmp_path):
    project, req, task, test, ver, dec = _setup_project(tmp_path)
    rows = build_matrix(project)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == req.id
    assert task.id in row["tasks"]
    assert test.id in row["tests"]
    assert ver.id in row["verifications"]
    assert dec.id in row["decisions"]
    assert row["verified"] is True


def test_build_matrix_unverified(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    rows = build_matrix(project)
    assert rows[0]["verified"] is False


def test_build_matrix_excludes_archived(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Old feature", "Deprecated.",
        status=ArtifactStatus.ARCHIVED,
    )
    rows = build_matrix(project)
    assert not any(r["id"] == req.id for r in rows)


def test_to_csv_headers(tmp_path):
    project, *_ = _setup_project(tmp_path)
    rows = build_matrix(project)
    csv_text = to_csv(rows)
    assert "REQ_ID" in csv_text
    assert "Tasks" in csv_text
    assert "Verified" in csv_text


def test_to_csv_row_content(tmp_path):
    project, req, task, *_ = _setup_project(tmp_path)
    rows = build_matrix(project)
    csv_text = to_csv(rows)
    assert req.id in csv_text
    assert task.id in csv_text
    assert "yes" in csv_text


def test_to_markdown_structure(tmp_path):
    project, req, *_ = _setup_project(tmp_path)
    rows = build_matrix(project)
    md = to_markdown(rows)
    assert "# Traceability Matrix" in md
    assert req.id in md
    assert "✓" in md


def test_export_project_writes_files(tmp_path):
    project, *_ = _setup_project(tmp_path)
    written = export_project(project, ExportFormat.BOTH)
    assert "csv" in written
    assert "markdown" in written
    assert written["csv"].exists()
    assert written["markdown"].exists()
    assert written["csv"].parent == project.root / "trace" / "exports"


def test_export_project_csv_only(tmp_path):
    project, *_ = _setup_project(tmp_path)
    written = export_project(project, ExportFormat.CSV)
    assert "csv" in written
    assert "markdown" not in written


def test_export_project_markdown_only(tmp_path):
    project, *_ = _setup_project(tmp_path)
    written = export_project(project, ExportFormat.MARKDOWN)
    assert "markdown" in written
    assert "csv" not in written


def test_export_cli_command(tmp_path):
    project, req, *_ = _setup_project(tmp_path)
    result = runner.invoke(app, ["export", str(project.root)])
    assert result.exit_code == 0, result.output
    assert "csv" in result.output
    assert "markdown" in result.output
    exports = list((project.root / "trace" / "exports").glob("*"))
    assert len(exports) == 2


def test_init_creates_project(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path / "newproj")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "newproj" / "exploration" / "memory.md").exists()
