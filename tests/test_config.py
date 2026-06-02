"""Tests for .specforge.yaml config file support."""
from pathlib import Path

import yaml
from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.config import (
    CONFIG_FILENAME,
    ProjectConfig,
    load_config,
    save_config,
    write_default_config,
)
from specforge_core.models import ArtifactKind
from specforge_core.project import Project

runner = CliRunner()


# ---------------------------------------------------------------------------
# load_config / save_config
# ---------------------------------------------------------------------------

def test_load_config_missing_returns_defaults(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.project_name == ""
    assert cfg.git_commit is False


def test_load_config_reads_yaml(tmp_path):
    (tmp_path / CONFIG_FILENAME).write_text(
        "project_name: MyProject\ngit_commit: true\n", encoding="utf-8"
    )
    cfg = load_config(tmp_path)
    assert cfg.project_name == "MyProject"
    assert cfg.git_commit is True


def test_load_config_tolerates_extra_keys(tmp_path):
    (tmp_path / CONFIG_FILENAME).write_text(
        "project_name: X\nunknown_key: ignored\n", encoding="utf-8"
    )
    cfg = load_config(tmp_path)
    assert cfg.project_name == "X"


def test_load_config_tolerates_null_name(tmp_path):
    (tmp_path / CONFIG_FILENAME).write_text("project_name:\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.project_name == ""


def test_save_config_roundtrip(tmp_path):
    cfg = ProjectConfig(project_name="Test Project", git_commit=True)
    save_config(tmp_path, cfg)
    loaded = load_config(tmp_path)
    assert loaded.project_name == "Test Project"
    assert loaded.git_commit is True


def test_write_default_config_creates_file(tmp_path):
    write_default_config(tmp_path)
    assert (tmp_path / CONFIG_FILENAME).exists()


def test_write_default_config_idempotent(tmp_path):
    write_default_config(tmp_path)
    content1 = (tmp_path / CONFIG_FILENAME).read_text()
    write_default_config(tmp_path)
    content2 = (tmp_path / CONFIG_FILENAME).read_text()
    assert content1 == content2


# ---------------------------------------------------------------------------
# Project.config
# ---------------------------------------------------------------------------

def test_project_config_property(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    assert project.config.git_commit is False


def test_project_config_lazy_cached(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    cfg1 = project.config
    cfg2 = project.config
    assert cfg1 is cfg2  # same object — cached


def test_project_reload_config(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    _ = project.config  # prime cache
    save_config(project.root, ProjectConfig(project_name="Updated", git_commit=True))
    reloaded = project.reload_config()
    assert reloaded.project_name == "Updated"
    assert project.config.git_commit is True


# ---------------------------------------------------------------------------
# git_commit default from config
# ---------------------------------------------------------------------------

def test_config_git_commit_default_used_by_add_idea(tmp_path):
    import git as gitpython
    repo = gitpython.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "t@t.com").release()

    proj = tmp_path / "proj"
    proj.mkdir()
    save_config(proj, ProjectConfig(project_name="P", git_commit=True))
    project = Project(proj)
    project.init()
    write_default_config(proj)
    save_config(proj, ProjectConfig(project_name="P", git_commit=True))

    result = runner.invoke(app, ["add-idea", str(proj), "Config idea", "Body."])
    assert result.exit_code == 0, result.output

    from specforge_core.gitwrap import artifact_log
    entries = artifact_log(tmp_path)
    assert any("Config idea" in e["message"] for e in entries)


# ---------------------------------------------------------------------------
# specforge config CLI command
# ---------------------------------------------------------------------------

def test_cli_config_show(tmp_path):
    Project(tmp_path / "proj").init()
    result = runner.invoke(app, ["config", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert "git_commit" in result.output
    assert "project_name" in result.output


def test_cli_config_set_project_name(tmp_path):
    Project(tmp_path / "proj").init()
    result = runner.invoke(app, ["config", str(tmp_path / "proj"), "--set", "project_name=FileConverter"])
    assert result.exit_code == 0, result.output
    cfg = load_config(tmp_path / "proj")
    assert cfg.project_name == "FileConverter"


def test_cli_config_set_git_commit_true(tmp_path):
    Project(tmp_path / "proj").init()
    runner.invoke(app, ["config", str(tmp_path / "proj"), "--set", "git_commit=true"])
    cfg = load_config(tmp_path / "proj")
    assert cfg.git_commit is True


def test_cli_config_set_git_commit_false(tmp_path):
    Project(tmp_path / "proj").init()
    runner.invoke(app, ["config", str(tmp_path / "proj"), "--set", "git_commit=true"])
    runner.invoke(app, ["config", str(tmp_path / "proj"), "--set", "git_commit=false"])
    cfg = load_config(tmp_path / "proj")
    assert cfg.git_commit is False


def test_cli_config_set_unknown_key(tmp_path):
    Project(tmp_path / "proj").init()
    result = runner.invoke(app, ["config", str(tmp_path / "proj"), "--set", "unknown_key=x"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# specforge init --name
# ---------------------------------------------------------------------------

def test_cli_init_name(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path / "proj"), "--name", "MyProject"])
    assert result.exit_code == 0, result.output
    cfg = load_config(tmp_path / "proj")
    assert cfg.project_name == "MyProject"


# ---------------------------------------------------------------------------
# project_name in status and report
# ---------------------------------------------------------------------------

def test_status_shows_project_name(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    save_config(project.root, ProjectConfig(project_name="FileConverter"))
    result = runner.invoke(app, ["status", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert "FileConverter" in result.output


def test_report_includes_project_name(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    save_config(project.root, ProjectConfig(project_name="FileConverter"))
    result = runner.invoke(app, ["report", str(tmp_path / "proj")])
    assert result.exit_code == 0, result.output
    assert "FileConverter" in result.output
