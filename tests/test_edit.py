"""Tests for specforge edit command."""
import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project

runner = CliRunner()


def _make_project(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", "The system shall export DXF files.",
        status=ArtifactStatus.APPROVED,
    )
    return project, artifact


def test_edit_calls_editor(tmp_path):
    project, artifact = _make_project(tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        result = runner.invoke(
            app, ["edit", str(tmp_path / "proj"), artifact.id],
            env={**os.environ, "EDITOR": "nano"},
        )
    assert result.exit_code == 0, result.output
    called_args = mock_run.call_args[0][0]
    assert "nano" in called_args
    assert str(artifact.path) in called_args


def test_edit_uses_visual_over_editor(tmp_path):
    project, artifact = _make_project(tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        runner.invoke(
            app, ["edit", str(tmp_path / "proj"), artifact.id],
            env={**os.environ, "VISUAL": "code", "EDITOR": "vi"},
        )
    called_args = mock_run.call_args[0][0]
    assert "code" in called_args


def test_edit_updated_body_readable_afterwards(tmp_path):
    project, artifact = _make_project(tmp_path)
    new_body = "The system shall export DXF files — UPDATED."

    def fake_run(cmd, **kwargs):
        assert artifact.path is not None
        text = artifact.path.read_text(encoding="utf-8")
        # Replace the body (everything after the closing ---)
        parts = text.split("---\n", 2)
        artifact.path.write_text(
            f"---\n{parts[1]}---\n{new_body}", encoding="utf-8"
        )

    with patch("subprocess.run", side_effect=fake_run):
        result = runner.invoke(
            app, ["edit", str(tmp_path / "proj"), artifact.id],
            env={**os.environ, "EDITOR": "fake_editor"},
        )
    assert result.exit_code == 0, result.output
    # New Project instance reads the updated file
    updated = Project(tmp_path / "proj").get_artifact(artifact.id)
    assert updated.body.strip() == new_body


def test_edit_no_editor_set(tmp_path):
    project, artifact = _make_project(tmp_path)
    env = {k: v for k, v in os.environ.items() if k not in ("EDITOR", "VISUAL")}
    result = runner.invoke(app, ["edit", str(tmp_path / "proj"), artifact.id], env=env)
    assert result.exit_code == 1
    assert "editor" in result.output.lower() or "EDITOR" in result.output


def test_edit_artifact_not_found(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    result = runner.invoke(
        app, ["edit", str(tmp_path / "proj"), "REQ-9999"],
        env={**os.environ, "EDITOR": "nano"},
    )
    assert result.exit_code == 1


def test_edit_reports_parse_error(tmp_path):
    project, artifact = _make_project(tmp_path)

    def corrupt_file(cmd, **kwargs):
        assert artifact.path is not None
        artifact.path.write_text("not valid yaml front matter\n", encoding="utf-8")

    with patch("subprocess.run", side_effect=corrupt_file):
        result = runner.invoke(
            app, ["edit", str(tmp_path / "proj"), artifact.id],
            env={**os.environ, "EDITOR": "bad_editor"},
        )
    assert "Warning" in result.output or "parse error" in result.output.lower()
