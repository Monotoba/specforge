"""Tests for tag support and the two new artifact kind commands."""
from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.models import ArtifactKind
from specforge_core.project import Project
from specforge_core.search import search_artifacts
from specforge_core.trace import TraceIndex

runner = CliRunner()


# ---------------------------------------------------------------------------
# Tags round-trip through create_artifact and filesystem
# ---------------------------------------------------------------------------

def test_tags_stored_and_loaded(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Body.", tags=["v1", "export"],
    )
    reloaded = project.get_artifact(artifact.id)
    assert "v1" in reloaded.tags
    assert "export" in reloaded.tags


def test_tags_in_sqlite(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Tagged idea", "Body.", tags=["alpha"])
    index = TraceIndex(project)
    index.rebuild()
    import sqlite3
    with sqlite3.connect(index.db_path) as conn:
        rows = conn.execute("SELECT tag FROM tags").fetchall()
    assert ("alpha",) in rows


# ---------------------------------------------------------------------------
# Tag filtering in search
# ---------------------------------------------------------------------------

def test_search_tag_filter(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    a = project.create_artifact(ArtifactKind.IDEA, "DXF idea", "Body.", tags=["export"])
    b = project.create_artifact(ArtifactKind.IDEA, "PDF idea", "Body.", tags=["print"])
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "idea", tags=["export"])
    ids = [r["id"] for r in results]
    assert a.id in ids
    assert b.id not in ids


def test_search_multi_tag_filter(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    a = project.create_artifact(ArtifactKind.IDEA, "DXF idea", ".", tags=["export", "v1"])
    b = project.create_artifact(ArtifactKind.IDEA, "PDF idea", ".", tags=["export"])
    TraceIndex(project).rebuild()

    results = search_artifacts(project, "idea", tags=["export", "v1"])
    ids = [r["id"] for r in results]
    assert a.id in ids
    assert b.id not in ids


# ---------------------------------------------------------------------------
# Tag filtering in list (CLI)
# ---------------------------------------------------------------------------

def test_cli_list_tag_filter(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Tagged", ".", tags=["foo"])
    project.create_artifact(ArtifactKind.IDEA, "Untagged", ".")

    result = runner.invoke(app, ["list", str(tmp_path / "proj"), "--tag", "foo"])
    assert result.exit_code == 0, result.output
    assert "Tagged" in result.output
    assert "Untagged" not in result.output


# ---------------------------------------------------------------------------
# --tag flag on add-* commands
# ---------------------------------------------------------------------------

def test_add_idea_with_tag(tmp_path):
    result = runner.invoke(app, [
        "add-idea", str(tmp_path), "My idea", "Body.", "--tag", "v1", "--tag", "draft",
    ])
    assert result.exit_code == 0, result.output
    artifact = Project(tmp_path).get_artifact("IDEA-0001")
    assert "v1" in artifact.tags
    assert "draft" in artifact.tags


def test_add_req_with_tag(tmp_path):
    result = runner.invoke(app, [
        "add-req", str(tmp_path), "My req", "--text", "Body.", "--tag", "must-have",
    ])
    assert result.exit_code == 0, result.output
    artifact = Project(tmp_path).get_artifact("REQ-0001")
    assert "must-have" in artifact.tags


# ---------------------------------------------------------------------------
# add-ref and add-conv
# ---------------------------------------------------------------------------

def test_add_ref(tmp_path):
    result = runner.invoke(app, [
        "add-ref", str(tmp_path), "ezdxf docs",
        "--text", "https://ezdxf.readthedocs.io",
    ])
    assert result.exit_code == 0, result.output
    assert "REF-0001" in result.output
    artifact = Project(tmp_path).get_artifact("REF-0001")
    assert artifact.kind == ArtifactKind.REFERENCE


def test_add_conv(tmp_path):
    result = runner.invoke(app, [
        "add-conv", str(tmp_path), "Design discussion 2026-06-01",
        "--text", "Discussed DXF vs SVG trade-offs with the team.",
        "--tag", "design",
    ])
    assert result.exit_code == 0, result.output
    assert "CONV-0001" in result.output
    artifact = Project(tmp_path).get_artifact("CONV-0001")
    assert artifact.kind == ArtifactKind.CONVERSATION
    assert "design" in artifact.tags


# ---------------------------------------------------------------------------
# graph command with Rich tree
# ---------------------------------------------------------------------------

def test_graph_command(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF", "Explore.")
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export.", source=idea.id,
    )
    TraceIndex(project).rebuild()

    result = runner.invoke(app, ["graph", str(tmp_path / "proj"), req.id])
    assert result.exit_code == 0, result.output
    assert req.id in result.output
    assert idea.id in result.output
    assert "source" in result.output


def test_graph_command_not_found(tmp_path):
    Project(tmp_path / "proj").init()
    result = runner.invoke(app, ["graph", str(tmp_path / "proj"), "REQ-9999"])
    assert result.exit_code == 1
