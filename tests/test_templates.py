"""Tests for artifact template system."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.models import ArtifactKind
from specforge_core.project import Project
from specforge_core.templates import list_templates, load_template

runner = CliRunner()


def _write_template(root: Path, kind: str, content: str) -> None:
    tdir = root / ".specforge" / "templates"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / f"{kind}.md").write_text(content, encoding="utf-8")


class TestLoadTemplate:
    def test_returns_empty_if_no_dir(self, tmp_path: Path) -> None:
        body, meta = load_template(tmp_path, "requirement")
        assert body == ""
        assert meta == {}

    def test_returns_empty_if_file_missing(self, tmp_path: Path) -> None:
        (tmp_path / ".specforge" / "templates").mkdir(parents=True)
        body, meta = load_template(tmp_path, "requirement")
        assert body == ""
        assert meta == {}

    def test_loads_plain_body(self, tmp_path: Path) -> None:
        _write_template(tmp_path, "task", "## What\n\nDo the thing.\n")
        body, meta = load_template(tmp_path, "task")
        assert "Do the thing" in body
        assert meta == {}

    def test_loads_front_matter_and_body(self, tmp_path: Path) -> None:
        _write_template(
            tmp_path, "requirement",
            "---\ntags: [v1.0, export]\n---\n\n## Purpose\n\nExport DXF.\n"
        )
        body, meta = load_template(tmp_path, "requirement")
        assert "Export DXF" in body
        assert meta.get("tags") == ["v1.0", "export"]

    def test_tolerates_invalid_front_matter(self, tmp_path: Path) -> None:
        _write_template(tmp_path, "task", "---\n: invalid yaml :\n---\n\nbody\n")
        body, meta = load_template(tmp_path, "task")
        assert meta == {}


class TestListTemplates:
    def test_empty_if_no_dir(self, tmp_path: Path) -> None:
        assert list_templates(tmp_path) == []

    def test_returns_kind_names(self, tmp_path: Path) -> None:
        _write_template(tmp_path, "requirement", "body")
        _write_template(tmp_path, "task", "body")
        kinds = list_templates(tmp_path)
        assert "requirement" in kinds
        assert "task" in kinds

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        _write_template(tmp_path, "task", "body")
        _write_template(tmp_path, "requirement", "body")
        _write_template(tmp_path, "idea", "body")
        assert list_templates(tmp_path) == ["idea", "requirement", "task"]


class TestProjectInitCreatesTemplates:
    def test_init_creates_templates_dir(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        assert (project.root / ".specforge" / "templates").is_dir()

    def test_init_writes_builtin_templates(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        tdir = project.root / ".specforge" / "templates"
        assert (tdir / "requirement.md").exists()
        assert (tdir / "task.md").exists()
        assert (tdir / "test.md").exists()

    def test_init_idempotent_does_not_overwrite(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        tdir = project.root / ".specforge" / "templates"
        (tdir / "requirement.md").write_text("custom content", encoding="utf-8")
        project.init()  # second init
        assert (tdir / "requirement.md").read_text() == "custom content"


class TestTemplateCLI:
    def test_template_list_shows_templates(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        result = runner.invoke(app, ["template", str(tmp_path), "list"])
        assert result.exit_code == 0
        assert "requirement" in result.output
        assert "task" in result.output
        assert "test" in result.output

    def test_template_list_no_specforge_dir(self, tmp_path: Path) -> None:
        # Neither init nor .specforge dir — 'list' still succeeds, shows empty
        result = runner.invoke(app, ["template", str(tmp_path), "list"])
        assert result.exit_code == 0
        # After init the builtin templates get created so table is shown
        assert "requirement" in result.output or "No templates" in result.output

    def test_template_new_creates_artifact(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        result = runner.invoke(
            app,
            ["template", str(tmp_path), "new", "requirement",
             "--title", "Export DXF", "--no-confirm"],
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        artifacts = project.artifacts()
        assert any(a.kind == ArtifactKind.REQUIREMENT for a in artifacts)

    def test_template_new_merges_template_tags(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        # Overwrite template with tags
        tdir = project.root / ".specforge" / "templates"
        (tdir / "task.md").write_text("---\ntags: [v1.0]\n---\n\nbody\n", encoding="utf-8")

        result = runner.invoke(
            app,
            ["template", str(tmp_path), "new", "task",
             "--title", "My Task", "--no-confirm"],
        )
        assert result.exit_code == 0
        artifacts = project.artifacts()
        tasks = [a for a in artifacts if a.kind == ArtifactKind.TASK]
        assert len(tasks) == 1
        assert "v1.0" in tasks[0].tags

    def test_template_new_unknown_kind_exits_1(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["template", str(tmp_path), "new", "nonexistent"],
        )
        assert result.exit_code == 1

    def test_template_new_no_template_exits_1(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        # Remove idea template (doesn't exist by default)
        result = runner.invoke(
            app,
            ["template", str(tmp_path), "new", "idea",
             "--title", "T", "--no-confirm"],
        )
        assert result.exit_code == 1
        assert "No template" in result.output

    def test_template_unknown_action_exits_1(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["template", str(tmp_path), "badaction"])
        assert result.exit_code == 1
