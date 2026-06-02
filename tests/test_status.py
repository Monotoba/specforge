"""Tests for the project status dashboard."""
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import specforge_daemon.api as _api
from specforge_cli.main import app as cli_app
from specforge_daemon.api import app as daemon_app
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.status import project_status
from specforge_core.trace import TraceIndex

cli_runner = CliRunner()
http_client = TestClient(daemon_app)


@pytest.fixture(autouse=True)
def reset_daemon(monkeypatch):
    if _api._watcher is not None:
        _api._watcher.stop()
        _api._watcher = None
    _api._active_project = None
    monkeypatch.setattr("specforge_daemon.watcher.ProjectWatcher.start", lambda self: None)
    yield
    if _api._watcher is not None:
        _api._watcher.stop()
        _api._watcher = None
    _api._active_project = None


# ---------------------------------------------------------------------------
# project_status core
# ---------------------------------------------------------------------------

def test_status_empty_project(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    data = project_status(project)
    assert data["total_artifacts"] == 0
    assert data["gate"] == "PASS"
    assert data["unverified_requirements"] == []
    assert data["open_tasks"] == []


def test_status_counts_by_kind(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    project.create_artifact(ArtifactKind.IDEA, "Idea 2", ".")
    project.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", ".", status=ArtifactStatus.APPROVED)
    data = project_status(project)
    assert data["kind_counts"]["idea"] == 2
    assert data["kind_counts"]["requirement"] == 1
    assert data["total_artifacts"] == 3


def test_status_fail_with_unverified_requirement(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", ".", status=ArtifactStatus.APPROVED,
    )
    data = project_status(project)
    assert data["gate"] == "FAIL"
    unverified_ids = [r["id"] for r in data["unverified_requirements"]]
    assert req.id in unverified_ids


def test_status_fail_with_open_task(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    task = project.create_artifact(ArtifactKind.TASK, "Build exporter", ".")
    data = project_status(project)
    assert data["gate"] == "FAIL"
    open_ids = [t["id"] for t in data["open_tasks"]]
    assert task.id in open_ids


def test_status_pass_when_verified_no_open_tasks(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    test_art = project.create_artifact(ArtifactKind.TEST, "DXF test", ".")
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", ".",
        status=ArtifactStatus.VERIFIED, verified_by=[test_art.id],
    )
    data = project_status(project)
    assert data["gate"] == "PASS"


def test_status_archived_task_not_open(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    task = project.create_artifact(ArtifactKind.TASK, "Done task", ".")
    project.update_status(task.id, ArtifactStatus.ARCHIVED)
    data = project_status(project)
    open_ids = [t["id"] for t in data["open_tasks"]]
    assert task.id not in open_ids


def test_status_breakdown_by_status(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", ".", status=ArtifactStatus.APPROVED)
    project.create_artifact(ArtifactKind.REQUIREMENT, "Req 2", ".", status=ArtifactStatus.VERIFIED)
    data = project_status(project)
    req_breakdown = data["breakdown"]["requirement"]
    assert req_breakdown["approved"] == 1
    assert req_breakdown["verified"] == 1


# ---------------------------------------------------------------------------
# CLI specforge status
# ---------------------------------------------------------------------------

def test_cli_status_output(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", ".", status=ArtifactStatus.APPROVED,
    )
    result = cli_runner.invoke(cli_app, ["status", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert "FAIL" in result.output
    assert "Export DXF" in result.output


def test_cli_status_pass(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = cli_runner.invoke(cli_app, ["status", str(tmp_path / "proj")])
    assert result.exit_code == 0
    assert "PASS" in result.output


# ---------------------------------------------------------------------------
# Daemon GET /status
# ---------------------------------------------------------------------------

def test_daemon_status(tmp_path):
    path = str(tmp_path / "proj")
    http_client.post("/projects/open", json={"path": path})
    project = _api._active_project
    assert project is not None
    project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    resp = http_client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_artifacts"] == 1
    assert "gate" in data
    assert "kind_counts" in data


def test_daemon_status_without_project():
    assert http_client.get("/status").status_code == 400
