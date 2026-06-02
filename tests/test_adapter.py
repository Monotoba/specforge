"""Tests for the AI adapter module and tool-call CLI/daemon entry points."""
import json
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import specforge_daemon.api as _api
from specforge_cli.main import app as cli_app
from specforge_daemon.api import app as daemon_app
from specforge_core.adapter import handle_tool_call
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
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
# handle_tool_call — core dispatch
# ---------------------------------------------------------------------------

def test_create_artifact(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = handle_tool_call(project, {
        "action": "create_artifact",
        "kind": "requirement",
        "title": "Export DXF",
        "body": "The system shall export DXF files.",
        "status": "approved",
        "tags": ["v1"],
    })
    assert result["ok"] is True
    data = result["result"]
    assert data["id"].startswith("REQ-")
    assert data["status"] == "approved"
    assert "v1" in data["tags"]


def test_create_artifact_bad_kind(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = handle_tool_call(project, {
        "action": "create_artifact",
        "kind": "nonexistent",
        "title": "X",
        "body": "Y",
    })
    assert result["ok"] is False
    assert result["error"] is not None


def test_promote_artifact(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF", "Explore.")
    result = handle_tool_call(project, {
        "action": "promote_artifact",
        "id": idea.id,
        "target_kind": "candidate",
    })
    assert result["ok"] is True
    assert result["result"]["id"].startswith("CAND-")
    assert result["result"]["source"] == idea.id


def test_update_status(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Body.", status=ArtifactStatus.APPROVED,
    )
    result = handle_tool_call(project, {
        "action": "update_status",
        "id": req.id,
        "status": "implemented",
    })
    assert result["ok"] is True
    assert result["result"]["status"] == "implemented"


def test_get_artifact(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Export DXF", "Body.")
    result = handle_tool_call(project, {"action": "get_artifact", "id": req.id})
    assert result["ok"] is True
    assert result["result"]["title"] == "Export DXF"


def test_get_artifact_missing(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = handle_tool_call(project, {"action": "get_artifact", "id": "REQ-9999"})
    assert result["ok"] is False


def test_list_artifacts(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    project.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", ".", status=ArtifactStatus.APPROVED)
    result = handle_tool_call(project, {"action": "list_artifacts", "kind": "idea"})
    assert result["ok"] is True
    assert len(result["result"]) == 1
    assert result["result"][0]["kind"] == "idea"


def test_list_artifacts_tag_filter(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Tagged", ".", tags=["foo"])
    project.create_artifact(ArtifactKind.IDEA, "Untagged", ".")
    result = handle_tool_call(project, {"action": "list_artifacts", "tag": "foo"})
    assert result["ok"] is True
    assert len(result["result"]) == 1
    assert result["result"][0]["title"] == "Tagged"


def test_search(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF files", "The system shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    TraceIndex(project).rebuild()
    result = handle_tool_call(project, {"action": "search", "query": "DXF"})
    assert result["ok"] is True
    ids = [r["id"] for r in result["result"]]
    assert req.id in ids


def test_context_pack(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = handle_tool_call(project, {"action": "context_pack"})
    assert result["ok"] is True
    pack = result["result"]
    assert "approved_requirements" in pack
    assert "open_tasks" in pack


def test_validate_clean(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = handle_tool_call(project, {"action": "validate"})
    assert result["ok"] is True
    assert result["result"]["ok"] is True


def test_validate_broken(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(
        ArtifactKind.REQUIREMENT, "Broken", ".", verified_by=["TEST-9999"],
    )
    result = handle_tool_call(project, {"action": "validate"})
    assert result["ok"] is True
    assert result["result"]["ok"] is False


def test_unknown_action(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = handle_tool_call(project, {"action": "explode"})
    assert result["ok"] is False
    assert "Unknown action" in result["error"]


# ---------------------------------------------------------------------------
# CLI tool-call command
# ---------------------------------------------------------------------------

def test_cli_tool_call_create(tmp_path):
    call = json.dumps({
        "action": "create_artifact",
        "kind": "idea",
        "title": "CLI tool-call idea",
        "body": "Created via tool-call.",
    })
    result = cli_runner.invoke(cli_app, ["tool-call", str(tmp_path), call])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["result"]["id"].startswith("IDEA-")


def test_cli_tool_call_bad_json(tmp_path):
    result = cli_runner.invoke(cli_app, ["tool-call", str(tmp_path), "{bad json}"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Daemon POST /tool-call
# ---------------------------------------------------------------------------

def test_daemon_tool_call(tmp_path):
    path = str(tmp_path / "proj")
    http_client.post("/projects/open", json={"path": path})
    resp = http_client.post("/tool-call", json={
        "action": "create_artifact",
        "kind": "idea",
        "title": "Daemon tool-call idea",
        "body": ".",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


def test_daemon_tool_call_without_project():
    resp = http_client.post("/tool-call", json={"action": "validate"})
    assert resp.status_code == 400
