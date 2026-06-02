"""Tests for link_artifact, promote link flags, and POST /artifacts/{id}/link."""
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import specforge_daemon.api as _api
from specforge_cli.main import app as cli_app
from specforge_daemon.api import app as daemon_app
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project

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
# Project.link_artifact
# ---------------------------------------------------------------------------

def test_link_adds_implements(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".")
    project.link_artifact(task.id, implements=[req.id])
    reloaded = project.get_artifact(task.id)
    assert req.id in reloaded.implements


def test_link_adds_verified_by(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    test_art = project.create_artifact(ArtifactKind.TEST, "Test", ".")
    project.link_artifact(req.id, verified_by=[test_art.id])
    reloaded = project.get_artifact(req.id)
    assert test_art.id in reloaded.verified_by


def test_link_no_duplicates(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".", implements=[req.id])
    project.link_artifact(task.id, implements=[req.id])  # add again
    reloaded = project.get_artifact(task.id)
    assert reloaded.implements.count(req.id) == 1


def test_link_adds_tags(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    project.link_artifact(idea.id, tags=["v1", "export"])
    reloaded = project.get_artifact(idea.id)
    assert "v1" in reloaded.tags
    assert "export" in reloaded.tags


def test_link_sets_source(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".")
    project.link_artifact(req.id, source=idea.id)
    reloaded = project.get_artifact(req.id)
    assert reloaded.source == idea.id


def test_link_preserves_existing_links(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", ".", status=ArtifactStatus.APPROVED)
    req2 = project.create_artifact(ArtifactKind.REQUIREMENT, "Req 2", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".", implements=[req.id])
    project.link_artifact(task.id, implements=[req2.id])
    reloaded = project.get_artifact(task.id)
    assert req.id in reloaded.implements
    assert req2.id in reloaded.implements


def test_link_unknown_artifact_raises(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    with pytest.raises(KeyError):
        project.link_artifact("REQ-9999", implements=["REQ-0001"])


# ---------------------------------------------------------------------------
# CLI specforge link
# ---------------------------------------------------------------------------

def test_cli_link_implements(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".")
    result = cli_runner.invoke(cli_app, [
        "link", str(tmp_path / "proj"), task.id, "--implements", req.id,
    ])
    assert result.exit_code == 0, result.output
    reloaded = project.get_artifact(task.id)
    assert req.id in reloaded.implements


def test_cli_link_not_found(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = cli_runner.invoke(cli_app, [
        "link", str(tmp_path / "proj"), "TASK-9999", "--implements", "REQ-0001",
    ])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# CLI specforge promote with link flags
# ---------------------------------------------------------------------------

def test_promote_with_implements(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    idea = project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    result = cli_runner.invoke(cli_app, [
        "promote", str(tmp_path / "proj"), idea.id, "task",
        "--implements", req.id,
    ])
    assert result.exit_code == 0, result.output
    task = project.get_artifact("TASK-0001")
    assert req.id in task.implements


def test_promote_with_tag(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    result = cli_runner.invoke(cli_app, [
        "promote", str(tmp_path / "proj"), idea.id, "candidate",
        "--tag", "v2",
    ])
    assert result.exit_code == 0, result.output
    cand = project.get_artifact("CAND-0001")
    assert "v2" in cand.tags


# ---------------------------------------------------------------------------
# Daemon POST /artifacts/{id}/link
# ---------------------------------------------------------------------------

def test_daemon_link(tmp_path):
    path = str(tmp_path / "proj")
    http_client.post("/projects/open", json={"path": path})
    project = _api._active_project
    assert project is not None
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".")

    resp = http_client.post(f"/artifacts/{task.id}/link", json={"implements": [req.id]})
    assert resp.status_code == 200
    reloaded = project.get_artifact(task.id)
    assert req.id in reloaded.implements


def test_daemon_link_not_found(tmp_path):
    http_client.post("/projects/open", json={"path": str(tmp_path / "proj")})
    resp = http_client.post("/artifacts/TASK-9999/link", json={"implements": ["REQ-0001"]})
    assert resp.status_code == 404
