"""Tests for unlink_artifact and specforge unlink, plus next_id cache optimization."""
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
# next_id uses artifact cache
# ---------------------------------------------------------------------------

def test_next_id_uses_cache(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    a1 = project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    # Prime the cache
    _ = project.artifacts()
    # Create second: must use the cached list, not a second filesystem scan
    a2 = project.create_artifact(ArtifactKind.IDEA, "Idea 2", ".")
    assert a1.id == "IDEA-0001"
    assert a2.id == "IDEA-0002"


def test_next_id_correct_after_multiple_creates(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    ids = [project.create_artifact(ArtifactKind.REQUIREMENT, f"Req {i}", ".").id for i in range(5)]
    assert ids == ["REQ-0001", "REQ-0002", "REQ-0003", "REQ-0004", "REQ-0005"]


def test_next_id_isolated_by_prefix(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    project.create_artifact(ArtifactKind.IDEA, "Idea 2", ".")
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".")
    assert req.id == "REQ-0001"  # independent of IDEA counter


# ---------------------------------------------------------------------------
# Project.unlink_artifact
# ---------------------------------------------------------------------------

def test_unlink_removes_implements(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".", implements=[req.id])
    project.unlink_artifact(task.id, implements=[req.id])
    reloaded = project.get_artifact(task.id)
    assert req.id not in reloaded.implements


def test_unlink_removes_only_specified_ids(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req1 = project.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", ".", status=ArtifactStatus.APPROVED)
    req2 = project.create_artifact(ArtifactKind.REQUIREMENT, "Req 2", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".", implements=[req1.id, req2.id])
    project.unlink_artifact(task.id, implements=[req1.id])
    reloaded = project.get_artifact(task.id)
    assert req1.id not in reloaded.implements
    assert req2.id in reloaded.implements


def test_unlink_clears_source(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "Idea", ".")
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", source=idea.id)
    project.unlink_artifact(req.id, clear_source=True)
    reloaded = project.get_artifact(req.id)
    assert reloaded.source is None


def test_unlink_removes_tags(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "Idea", ".", tags=["v1", "export"])
    project.unlink_artifact(idea.id, tags=["v1"])
    reloaded = project.get_artifact(idea.id)
    assert "v1" not in reloaded.tags
    assert "export" in reloaded.tags


def test_unlink_nonexistent_value_is_noop(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".")
    # REQ-9999 was never linked — should not raise
    project.unlink_artifact(task.id, implements=["REQ-9999"])
    reloaded = project.get_artifact(task.id)
    assert reloaded.implements == []


def test_unlink_unknown_artifact_raises(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    with pytest.raises(KeyError):
        project.unlink_artifact("TASK-9999", implements=["REQ-0001"])


# ---------------------------------------------------------------------------
# CLI specforge unlink
# ---------------------------------------------------------------------------

def test_cli_unlink_implements(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".", implements=[req.id])
    result = cli_runner.invoke(cli_app, [
        "unlink", str(tmp_path / "proj"), task.id, "--implements", req.id,
    ])
    assert result.exit_code == 0, result.output
    reloaded = project.get_artifact(task.id)
    assert req.id not in reloaded.implements


def test_cli_unlink_not_found(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = cli_runner.invoke(cli_app, [
        "unlink", str(tmp_path / "proj"), "TASK-9999", "--implements", "REQ-0001",
    ])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Daemon POST /artifacts/{id}/unlink
# ---------------------------------------------------------------------------

def test_daemon_unlink(tmp_path):
    path = str(tmp_path / "proj")
    http_client.post("/projects/open", json={"path": path})
    project = _api._active_project
    assert project is not None
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Req", ".", status=ArtifactStatus.APPROVED)
    task = project.create_artifact(ArtifactKind.TASK, "Task", ".", implements=[req.id])

    resp = http_client.post(f"/artifacts/{task.id}/unlink", json={"implements": [req.id]})
    assert resp.status_code == 200
    reloaded = project.get_artifact(task.id)
    assert req.id not in reloaded.implements


def test_daemon_unlink_not_found(tmp_path):
    http_client.post("/projects/open", json={"path": str(tmp_path / "proj")})
    resp = http_client.post("/artifacts/TASK-9999/unlink", json={"implements": ["REQ-0001"]})
    assert resp.status_code == 404
