"""Tests for the six new add-* CLI commands."""
from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project

runner = CliRunner()


def test_add_decision(tmp_path):
    result = runner.invoke(app, [
        "add-decision", str(tmp_path), "Use SQLite for trace index",
        "--text", "SQLite is embedded and requires no server.",
    ])
    assert result.exit_code == 0, result.output
    assert "DEC-0001" in result.output
    artifacts = Project(tmp_path).artifacts()
    assert len(artifacts) == 1
    assert artifacts[0].kind == ArtifactKind.DECISION
    assert artifacts[0].status == ArtifactStatus.APPROVED


def test_add_assumption(tmp_path):
    result = runner.invoke(app, [
        "add-assumption", str(tmp_path), "Users have Python 3.11+",
        "--text", "We assume the host has Python 3.11 or newer.",
    ])
    assert result.exit_code == 0, result.output
    assert "ASM-0001" in result.output


def test_add_constraint(tmp_path):
    result = runner.invoke(app, [
        "add-constraint", str(tmp_path), "Must run offline",
        "--text", "No external network calls at runtime.",
    ])
    assert result.exit_code == 0, result.output
    assert "CON-0001" in result.output


def test_add_task_with_implements(tmp_path):
    project = Project(tmp_path)
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    result = runner.invoke(app, [
        "add-task", str(tmp_path), "Build DXF exporter",
        "--text", "Implement the DXF export module.",
        "--implements", req.id,
    ])
    assert result.exit_code == 0, result.output
    assert "TASK-0001" in result.output
    task = Project(tmp_path).get_artifact("TASK-0001")
    assert req.id in task.implements


def test_add_task_with_depends_on(tmp_path):
    project = Project(tmp_path)
    project.init()
    task1 = project.create_artifact(ArtifactKind.TASK, "Setup DB", "Create schema.")
    result = runner.invoke(app, [
        "add-task", str(tmp_path), "Migrate data",
        "--text", "Run migration.",
        "--depends-on", task1.id,
    ])
    assert result.exit_code == 0, result.output
    task2 = Project(tmp_path).get_artifact("TASK-0002")
    assert task1.id in task2.depends_on


def test_add_test_with_req_link(tmp_path):
    project = Project(tmp_path)
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    result = runner.invoke(app, [
        "add-test", str(tmp_path), "DXF export passes",
        "--text", "Run export and verify output file.",
        "--req", req.id,
    ])
    assert result.exit_code == 0, result.output
    assert "TEST-0001" in result.output
    test_art = Project(tmp_path).get_artifact("TEST-0001")
    assert req.id in test_art.related_requirements


def test_add_verification_with_links(tmp_path):
    project = Project(tmp_path)
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    test_art = project.create_artifact(ArtifactKind.TEST, "DXF test", "Test body.")
    result = runner.invoke(app, [
        "add-verification", str(tmp_path), "DXF export verified",
        "--text", "All tests passed on 2026-06-01.",
        "--req", req.id,
        "--test", test_art.id,
    ])
    assert result.exit_code == 0, result.output
    assert "VER-0001" in result.output
    ver = Project(tmp_path).get_artifact("VER-0001")
    assert req.id in ver.related_requirements
    assert test_art.id in ver.verified_by


def test_add_decision_with_req_link(tmp_path):
    project = Project(tmp_path)
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "Shall export DXF.",
        status=ArtifactStatus.APPROVED,
    )
    result = runner.invoke(app, [
        "add-decision", str(tmp_path), "Use ezdxf library",
        "--text", "ezdxf is the best Python DXF library.",
        "--req", req.id,
    ])
    assert result.exit_code == 0, result.output
    dec = Project(tmp_path).get_artifact("DEC-0001")
    assert req.id in dec.related_requirements
