import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import specforge_daemon.api as _api
from specforge_cli.main import app as cli_app
from specforge_daemon.api import app as daemon_app
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.search import search_artifacts
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


def _populate(project: Project):
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF files",
        "The system shall export project drawings as DXF files.",
        status=ArtifactStatus.APPROVED,
    )
    task = project.create_artifact(
        ArtifactKind.TASK, "Build DXF exporter",
        "Implement the ezdxf-based export module.",
        implements=[req.id],
    )
    dec = project.create_artifact(
        ArtifactKind.DECISION, "Use ezdxf library",
        "ezdxf is the most actively maintained Python DXF library.",
        related_requirements=[req.id],
    )
    return req, task, dec


# ---------------------------------------------------------------------------
# Core search function
# ---------------------------------------------------------------------------

def test_search_finds_by_title_keyword(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req, *_ = _populate(project)
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "DXF")
    ids = [r["id"] for r in results]
    assert req.id in ids


def test_search_finds_by_body_keyword(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _, task, _ = _populate(project)
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "ezdxf")
    ids = [r["id"] for r in results]
    assert task.id in ids


def test_search_multi_term_requires_all(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    # "DXF export" matches req and task titles; "ezdxf" only matches task body/dec body
    results = search_artifacts(project, "DXF ezdxf")
    # Only artifacts containing BOTH terms
    for r in results:
        text = (str(r["title"]) + str(r["snippet"])).lower()
        assert "dxf" in text
        assert "ezdxf" in text


def test_search_empty_query_returns_nothing(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    assert search_artifacts(project, "") == []
    assert search_artifacts(project, "   ") == []


def test_search_no_match_returns_empty(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    assert search_artifacts(project, "nonexistent_zzzzzz") == []


def test_search_filter_by_kind(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "DXF", kinds=[ArtifactKind.REQUIREMENT])
    assert all(r["kind"] == "requirement" for r in results)


def test_search_filter_by_status(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "DXF", statuses=[ArtifactStatus.APPROVED])
    assert all(r["status"] == "approved" for r in results)


def test_search_result_has_snippet(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "ezdxf")
    assert all("snippet" in r for r in results)
    # Snippet for task/dec body should contain "ezdxf"
    assert any("ezdxf" in str(r["snippet"]).lower() for r in results)


def test_search_snippet_truncated(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    long_body = "ezdxf " + ("x" * 200)
    project.create_artifact(ArtifactKind.TASK, "Long task", long_body)
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "ezdxf")
    snippet = str(results[0]["snippet"])
    assert len(snippet) <= 122  # 120 chars + "…"
    assert snippet.endswith("…")


def test_search_case_insensitive(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "DXF Export", "Export DXF drawings.")
    TraceIndex(project).rebuild()

    assert search_artifacts(project, "dxf export")
    assert search_artifacts(project, "DXF EXPORT")
    assert search_artifacts(project, "Dxf Export")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_search_finds_results(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req, *_ = _populate(project)
    TraceIndex(project).rebuild()

    result = cli_runner.invoke(cli_app, ["search", str(tmp_path / "proj"), "DXF"])
    assert result.exit_code == 0, result.output
    assert req.id in result.output


def test_cli_search_no_results_message(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    TraceIndex(project).rebuild()

    result = cli_runner.invoke(cli_app, ["search", str(tmp_path / "proj"), "zzz_no_match"])
    assert result.exit_code == 0
    assert "No results" in result.output


def test_cli_search_kind_filter(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _populate(project)
    TraceIndex(project).rebuild()

    result = cli_runner.invoke(cli_app, ["search", str(tmp_path / "proj"), "DXF", "--kind", "requirement"])
    assert result.exit_code == 0, result.output
    assert "REQ-" in result.output
    assert "TASK-" not in result.output


# ---------------------------------------------------------------------------
# Daemon endpoint
# ---------------------------------------------------------------------------

def test_daemon_search_returns_results(tmp_path):
    path = str(tmp_path / "proj")
    http_client.post("/projects/open", json={"path": path})
    project = _api._active_project
    assert project is not None
    _populate(project)
    http_client.post("/trace/rebuild", json={})

    resp = http_client.get("/search?q=DXF")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all("id" in r and "snippet" in r for r in data)


def test_daemon_search_without_project():
    assert http_client.get("/search?q=DXF").status_code == 400


def test_daemon_search_empty_returns_empty(tmp_path):
    path = str(tmp_path / "proj")
    http_client.post("/projects/open", json={"path": path})
    http_client.post("/trace/rebuild", json={})

    resp = http_client.get("/search?q=zzz_no_match")
    assert resp.status_code == 200
    assert resp.json() == []
