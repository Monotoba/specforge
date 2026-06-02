"""Integration tests for specforge_daemon REST API."""
import pytest
from fastapi.testclient import TestClient

import specforge_daemon.api as _api
from specforge_daemon.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_daemon(monkeypatch):
    """Reset daemon globals and disable the background watcher for all daemon tests.

    The watcher's background thread races against explicit rebuild calls in tests,
    causing intermittent 'database is locked' and 'no such table' errors. Tests
    that need accurate trace data call POST /trace/rebuild explicitly instead.
    """
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


@pytest.fixture
def proj(tmp_path):
    """Open a project and return its path string."""
    path = str(tmp_path / "demo")
    client.post("/projects/open", json={"path": path})
    return path


@pytest.fixture
def req_id(proj):
    """Create one approved requirement and return its ID."""
    resp = client.post("/artifacts", json={
        "kind": "requirement", "title": "Export DXF", "body": "Shall export DXF.",
        "status": "approved",
    })
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Health / static
# ---------------------------------------------------------------------------

def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ui_returns_html():
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "SpecForge" in resp.text
    assert resp.headers["content-type"].startswith("text/html")


# ---------------------------------------------------------------------------
# No-project guard (400)
# ---------------------------------------------------------------------------

def test_list_artifacts_without_project():
    resp = client.get("/artifacts")
    assert resp.status_code == 400


def test_create_artifact_without_project():
    resp = client.post("/artifacts", json={"kind": "idea", "title": "X", "body": "Y"})
    assert resp.status_code == 400


def test_context_pack_without_project():
    assert client.get("/context-pack").status_code == 400


def test_report_without_project():
    assert client.get("/report").status_code == 400


def test_validate_without_project():
    assert client.get("/validate").status_code == 400


# ---------------------------------------------------------------------------
# Open project
# ---------------------------------------------------------------------------

def test_open_project(tmp_path):
    path = str(tmp_path / "proj")
    resp = client.post("/projects/open", json={"path": path})
    assert resp.status_code == 200
    assert "path" in resp.json()


def test_open_project_initialises_scaffold(tmp_path):
    path = tmp_path / "proj"
    client.post("/projects/open", json={"path": str(path)})
    assert (path / "exploration" / "memory.md").exists()
    assert (path / "specification" / "requirements").is_dir()


# ---------------------------------------------------------------------------
# Artifact CRUD
# ---------------------------------------------------------------------------

def test_create_and_list_artifact(proj):
    resp = client.post("/artifacts", json={
        "kind": "idea", "title": "DXF export", "body": "Explore DXF.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"].startswith("IDEA-")

    listing = client.get("/artifacts").json()
    assert any(a["id"] == data["id"] for a in listing)


def test_list_artifacts_filtered_by_kind(proj):
    client.post("/artifacts", json={"kind": "idea", "title": "Idea 1", "body": "."})
    client.post("/artifacts", json={
        "kind": "requirement", "title": "Req 1", "body": ".", "status": "approved",
    })
    ideas = client.get("/artifacts?kind=idea").json()
    assert all(a["kind"] == "idea" for a in ideas)
    assert len(ideas) == 1


def test_get_artifact(proj):
    artifact_id = client.post("/artifacts", json={
        "kind": "idea", "title": "Get me", "body": "Body.",
    }).json()["id"]

    resp = client.get(f"/artifacts/{artifact_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get me"


def test_get_artifact_not_found(proj):
    assert client.get("/artifacts/REQ-9999").status_code == 404


def test_create_artifact_with_source_link(proj):
    idea_id = client.post("/artifacts", json={
        "kind": "idea", "title": "DXF", "body": ".",
    }).json()["id"]
    req_id = client.post("/artifacts", json={
        "kind": "requirement", "title": "Export DXF", "body": "Shall.",
        "status": "approved", "source": idea_id,
    }).json()["id"]

    artifact = client.get(f"/artifacts/{req_id}").json()
    assert artifact["source"] == idea_id


# ---------------------------------------------------------------------------
# Promote
# ---------------------------------------------------------------------------

def test_promote_idea_to_candidate(proj):
    idea_id = client.post("/artifacts", json={
        "kind": "idea", "title": "DXF export", "body": "Explore.",
    }).json()["id"]

    resp = client.post(f"/artifacts/{idea_id}/promote", json={"target_kind": "candidate"})
    assert resp.status_code == 200
    cand_id = resp.json()["id"]
    assert cand_id.startswith("CAND-")

    cand = client.get(f"/artifacts/{cand_id}").json()
    assert cand["source"] == idea_id
    assert cand["status"] == "proposed"


def test_promote_nonexistent_returns_404(proj):
    resp = client.post("/artifacts/IDEA-9999/promote", json={"target_kind": "candidate"})
    assert resp.status_code == 404


def test_promote_with_title_override(proj):
    idea_id = client.post("/artifacts", json={
        "kind": "idea", "title": "Old title", "body": ".",
    }).json()["id"]
    resp = client.post(f"/artifacts/{idea_id}/promote", json={
        "target_kind": "candidate", "title": "New title",
    })
    cand = client.get(f"/artifacts/{resp.json()['id']}").json()
    assert cand["title"] == "New title"


# ---------------------------------------------------------------------------
# Update status
# ---------------------------------------------------------------------------

def test_update_status(proj, req_id):
    resp = client.patch(f"/artifacts/{req_id}/status", json={"status": "implemented"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "implemented"

    reloaded = client.get(f"/artifacts/{req_id}").json()
    assert reloaded["status"] == "implemented"


def test_update_status_nonexistent_returns_404(proj):
    assert client.patch("/artifacts/REQ-9999/status", json={"status": "archived"}).status_code == 404


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------

def test_rebuild_trace(proj, req_id):
    resp = client.post("/trace/rebuild", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "unverified_requirements" in data
    assert any(r["id"] == req_id for r in data["unverified_requirements"])


def test_trace_graph(proj, req_id):
    client.post("/trace/rebuild", json={})
    resp = client.get(f"/trace/{req_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["artifact"]["id"] == req_id


def test_trace_graph_not_found(proj):
    assert client.get("/trace/REQ-9999").status_code == 404


def test_trace_graph_includes_source_link(proj):
    idea_id = client.post("/artifacts", json={
        "kind": "idea", "title": "DXF", "body": ".",
    }).json()["id"]
    req_id = client.post("/artifacts", json={
        "kind": "requirement", "title": "Export DXF", "body": ".", "status": "approved",
        "source": idea_id,
    }).json()["id"]
    client.post("/trace/rebuild", json={})
    graph = client.get(f"/trace/{req_id}").json()
    assert any(l["dst_id"] == idea_id for l in graph["outgoing"])


# ---------------------------------------------------------------------------
# Context pack
# ---------------------------------------------------------------------------

def test_context_pack_structure(proj, req_id):
    resp = client.get("/context-pack")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("approved_requirements", "open_tasks", "unverified_requirements", "links"):
        assert key in data
    assert any(r["id"] == req_id for r in data["approved_requirements"])


def test_context_pack_unverified_includes_req(proj, req_id):
    client.post("/trace/rebuild", json={})
    data = client.get("/context-pack").json()
    assert any(r["id"] == req_id for r in data["unverified_requirements"])


# ---------------------------------------------------------------------------
# Acceptance report
# ---------------------------------------------------------------------------

def test_report_returns_markdown(proj, req_id):
    resp = client.get("/report")
    assert resp.status_code == 200
    assert "Acceptance Report" in resp.text
    assert req_id in resp.text
    assert "FAIL" in resp.text  # unverified requirement present


def test_report_pass_when_verified(proj):
    test_id = client.post("/artifacts", json={
        "kind": "test", "title": "DXF test", "body": ".",
    }).json()["id"]
    client.post("/artifacts", json={
        "kind": "requirement", "title": "Export DXF", "body": ".",
        "status": "verified", "verified_by": [test_id],
    })
    resp = client.get("/report")
    assert "PASS" in resp.text


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_export_writes_files(proj, req_id, tmp_path):
    resp = client.get("/export")
    assert resp.status_code == 200
    data = resp.json()
    assert "csv" in data
    assert "markdown" in data


def test_export_csv_only(proj, req_id):
    resp = client.get("/export?fmt=csv")
    assert resp.status_code == 200
    assert "csv" in resp.json()
    assert "markdown" not in resp.json()


def test_export_matrix_inline_markdown(proj, req_id):
    resp = client.get("/export/matrix")
    assert resp.status_code == 200
    assert "Traceability Matrix" in resp.json()


def test_export_matrix_inline_csv(proj, req_id):
    resp = client.get("/export/matrix?fmt=csv")
    assert resp.status_code == 200
    assert "REQ_ID" in resp.json()


# ---------------------------------------------------------------------------
# Git log
# ---------------------------------------------------------------------------

def test_git_log_empty_outside_repo(proj):
    resp = client.get("/git/log")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def test_validate_clean_project(proj, req_id):
    resp = client.get("/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["errors"] == []


def test_validate_detects_broken_link(proj):
    client.post("/artifacts", json={
        "kind": "requirement", "title": "Broken", "body": ".",
        "status": "approved", "verified_by": ["TEST-9999"],
    })
    resp = client.get("/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert len(data["errors"]) > 0
