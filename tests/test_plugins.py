"""Tests for plugin loader and dispatcher."""
from __future__ import annotations

from pathlib import Path

import pytest

from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.plugins import load_plugins
from specforge_core.project import Project


def _write_plugin(plugin_dir: Path, name: str, body: str) -> Path:
    path = plugin_dir / name
    path.write_text(body, encoding="utf-8")
    return path


class TestLoadPlugins:
    def test_returns_empty_if_no_dir(self, tmp_path: Path) -> None:
        assert load_plugins(tmp_path) == []

    def test_returns_empty_if_dir_is_empty(self, tmp_path: Path) -> None:
        (tmp_path / ".specforge" / "plugins").mkdir(parents=True)
        assert load_plugins(tmp_path) == []

    def test_loads_plugin_with_on_event(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / ".specforge" / "plugins"
        plugin_dir.mkdir(parents=True)
        _write_plugin(plugin_dir, "myplugin.py", "def on_event(e, a, p): pass\n")
        modules = load_plugins(tmp_path)
        assert len(modules) == 1
        assert hasattr(modules[0], "on_event")

    def test_loads_plugin_without_on_event(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / ".specforge" / "plugins"
        plugin_dir.mkdir(parents=True)
        _write_plugin(plugin_dir, "noop.py", "x = 42\n")
        modules = load_plugins(tmp_path)
        assert len(modules) == 1
        assert not hasattr(modules[0], "on_event")

    def test_ignores_non_py_files(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / ".specforge" / "plugins"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "README.md").write_text("# docs")
        (plugin_dir / "example.py.disabled").write_text("def on_event(e, a, p): pass")
        assert load_plugins(tmp_path) == []

    def test_catches_import_error(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / ".specforge" / "plugins"
        plugin_dir.mkdir(parents=True)
        _write_plugin(plugin_dir, "broken.py", "raise ImportError('oops')\n")
        modules = load_plugins(tmp_path)
        assert modules == []

    def test_loads_multiple_plugins(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / ".specforge" / "plugins"
        plugin_dir.mkdir(parents=True)
        _write_plugin(plugin_dir, "a.py", "def on_event(e, a, p): pass\n")
        _write_plugin(plugin_dir, "b.py", "def on_event(e, a, p): pass\n")
        modules = load_plugins(tmp_path)
        assert len(modules) == 2


class TestFirePluginEvent:
    def test_plugin_on_event_called_with_correct_args(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "recorder.py",
            "calls = []\ndef on_event(event, artifact, project):\n    calls.append((event, artifact.id, artifact.kind.value))\n",
        )

        artifact = project.create_artifact(ArtifactKind.IDEA, "Test", "body")

        # Inspect the cached module instances (same objects that received on_event calls)
        assert project._plugin_cache is not None
        recorded_mods = [m for m in project._plugin_cache if hasattr(m, "calls")]
        assert len(recorded_mods) == 1
        assert ("artifact.created", artifact.id, "idea") in recorded_mods[0].calls

    def test_plugin_exception_does_not_prevent_mutation(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "crasher.py",
            "def on_event(event, artifact, project):\n    raise RuntimeError('plugin crash')\n",
        )

        # Should not raise — mutation should succeed
        artifact = project.create_artifact(ArtifactKind.IDEA, "Test", "body")
        assert artifact.id.startswith("IDEA-")

    def test_plugin_without_on_event_is_skipped(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(plugin_dir, "noop.py", "x = 42\n")
        # Should not raise
        artifact = project.create_artifact(ArtifactKind.IDEA, "Test", "body")
        assert artifact.id.startswith("IDEA-")

    def test_plugin_cache_reused(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(plugin_dir, "a.py", "def on_event(e, a, p): pass\n")

        project.create_artifact(ArtifactKind.IDEA, "Idea 1", "body")
        cache1 = project._plugin_cache
        project.create_artifact(ArtifactKind.IDEA, "Idea 2", "body")
        cache2 = project._plugin_cache

        # Same list object — not re-loaded
        assert cache1 is cache2


class TestPluginIntegration:
    def _get_seen(self, project: Project) -> list[str]:
        """Get the 'seen' list from the first plugin in the cache."""
        assert project._plugin_cache is not None
        for mod in project._plugin_cache:
            seen = getattr(mod, "seen", None)
            if seen is not None:
                return seen
        return []

    def test_plugin_fired_on_create_artifact(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "events.py",
            "seen = []\ndef on_event(event, artifact, project):\n    seen.append(event)\n",
        )
        project.create_artifact(ArtifactKind.IDEA, "Test", "body")
        assert "artifact.created" in self._get_seen(project)

    def test_plugin_fired_on_update_status(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "events.py",
            "seen = []\ndef on_event(event, artifact, project):\n    seen.append(event)\n",
        )
        artifact = project.create_artifact(ArtifactKind.IDEA, "Test", "body")
        project.update_status(artifact.id, ArtifactStatus.PROPOSED)
        assert "artifact.status_changed" in self._get_seen(project)

    def test_plugin_fired_on_promote_artifact(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "events.py",
            "seen = []\ndef on_event(event, artifact, project):\n    seen.append(event)\n",
        )
        artifact = project.create_artifact(ArtifactKind.IDEA, "Test", "body")
        project.promote_artifact(artifact.id, ArtifactKind.CANDIDATE)
        assert "artifact.promoted" in self._get_seen(project)

    def test_plugin_fired_on_link_artifact(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "events.py",
            "seen = []\ndef on_event(event, artifact, project):\n    seen.append(event)\n",
        )
        artifact = project.create_artifact(ArtifactKind.IDEA, "Test", "body")
        project.link_artifact(artifact.id, tags=["v1"])
        assert "artifact.linked" in self._get_seen(project)

    def test_plugin_fired_on_unlink_artifact(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        plugin_dir = tmp_path / ".specforge" / "plugins"
        _write_plugin(
            plugin_dir,
            "events.py",
            "seen = []\ndef on_event(event, artifact, project):\n    seen.append(event)\n",
        )
        artifact = project.create_artifact(
            ArtifactKind.IDEA, "Test", "body", tags=["v1"]
        )
        project.unlink_artifact(artifact.id, tags=["v1"])
        assert "artifact.unlinked" in self._get_seen(project)


class TestPluginCLI:
    def test_plugin_list_no_plugins(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from specforge_cli.main import app

        project = Project(tmp_path)
        project.init()
        # Remove all .py files so it shows the empty message
        for f in (project.root / ".specforge" / "plugins").glob("*.py"):
            f.unlink()

        runner = CliRunner()
        result = runner.invoke(app, ["plugin", str(tmp_path)])
        assert result.exit_code == 0
        assert "No plugins" in result.stdout

    def test_plugin_list_shows_plugin_file(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from specforge_cli.main import app

        project = Project(tmp_path)
        project.init()
        plugin_dir = project.root / ".specforge" / "plugins"
        _write_plugin(plugin_dir, "my_hook.py", "def on_event(e, a, p): pass\n")

        runner = CliRunner()
        result = runner.invoke(app, ["plugin", str(tmp_path)])
        assert result.exit_code == 0
        assert "my_hook.py" in result.stdout

    def test_project_init_creates_plugins_dir(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        assert (project.root / ".specforge" / "plugins").is_dir()
        assert (project.root / ".specforge" / "plugins" / "example_plugin.py.disabled").exists()
