"""Tests for specforge check CI command and artifacts() cache."""
import time

from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project

runner = CliRunner()


# ---------------------------------------------------------------------------
# artifacts() cache
# ---------------------------------------------------------------------------

def test_cache_returns_same_list_on_second_call(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    first = project.artifacts()
    second = project.artifacts()
    assert first is second  # identical list object — cache hit


def test_cache_invalidated_after_create(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    first = project.artifacts()
    project.create_artifact(ArtifactKind.IDEA, "Idea 2", ".")
    second = project.artifacts()
    assert first is not second
    assert len(second) == 2


def test_cache_invalidated_after_update_status(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED,
    )
    _ = project.artifacts()  # prime cache
    project.update_status(req.id, ArtifactStatus.IMPLEMENTED)
    reloaded = project.get_artifact(req.id)
    assert reloaded.status == ArtifactStatus.IMPLEMENTED


def test_cache_detects_external_file_change(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    artifact = project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    _ = project.artifacts()  # prime cache
    assert artifact.path is not None
    # Simulate an external write (e.g. user edits file directly)
    time.sleep(0.01)  # ensure mtime differs
    artifact.path.touch()
    # A new Project instance (or same one after mtime changes) must re-scan
    project2 = Project(tmp_path / "proj")
    result = project2.artifacts()
    assert len(result) == 1


def test_invalidate_cache_forces_rescan(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    first = project.artifacts()
    project.invalidate_cache()
    second = project.artifacts()
    assert first is not second  # different list objects after forced invalidation
    assert len(first) == len(second)


# ---------------------------------------------------------------------------
# specforge check
# ---------------------------------------------------------------------------

def test_check_passes_empty_project(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = runner.invoke(app, ["check", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_check_fails_with_unverified_requirement(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", ".", status=ArtifactStatus.APPROVED,
    )
    result = runner.invoke(app, ["check", str(tmp_path / "proj")])
    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert "Export DXF" in result.output


def test_check_fails_with_open_task(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.TASK, "Build DXF exporter", ".")
    result = runner.invoke(app, ["check", str(tmp_path / "proj")])
    assert result.exit_code == 1
    assert "Build DXF exporter" in result.output


def test_check_fails_with_broken_link(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Broken req", ".", verified_by=["TEST-9999"],
    )
    result = runner.invoke(app, ["check", str(tmp_path / "proj")])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_check_passes_when_all_verified_no_open_tasks(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    test_art = project.create_artifact(ArtifactKind.TEST, "DXF test", ".")
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", ".",
        status=ArtifactStatus.VERIFIED, verified_by=[test_art.id],
    )
    result = runner.invoke(app, ["check", str(tmp_path / "proj")])
    assert result.exit_code == 0
    assert "PASS" in result.output
