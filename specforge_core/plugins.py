"""Plugin loader and dispatcher for artifact events.

Plugins are Python files placed in .specforge/plugins/*.py. Each file may
define an on_event(event, artifact, project) function. Plugins are loaded
once per Project instance (lazy, on first fire_plugin_event call).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

PLUGINS_DIR = ".specforge/plugins"

_EXAMPLE_PLUGIN = """\
# SpecForge plugin example — rename to *.py to activate.
#
# on_event is called synchronously after each artifact mutation.
# Exceptions are caught and logged to stderr; the mutation still completes.
#
# event: "artifact.created" | "artifact.promoted" | "artifact.status_changed"
#        "artifact.linked"  | "artifact.unlinked"
# artifact: specforge_core.models.Artifact
# project:  specforge_core.project.Project

def on_event(event, artifact, project):
    if event == "artifact.created":
        print(f"[plugin] New artifact: {artifact.id} — {artifact.title}")
"""


def load_plugins(root: Path) -> list[ModuleType]:
    """Load all *.py files from <root>/.specforge/plugins/. Returns loaded modules.

    Import errors are caught and logged to stderr — a broken plugin won't
    prevent other plugins or the artifact mutation from running.
    """
    plugin_dir = root / PLUGINS_DIR
    if not plugin_dir.is_dir():
        return []

    modules: list[ModuleType] = []
    for path in sorted(plugin_dir.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(
                f"specforge_plugin_{path.stem}", path
            )
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            modules.append(mod)
        except Exception as exc:
            print(f"Plugin {path.name} load error: {exc}", file=sys.stderr)
    return modules


def fire_plugin_event(project: object, event: str, artifact: object) -> None:
    """Call on_event(event, artifact, project) in each plugin. Never raises.

    Plugins are loaded once and cached on project._plugin_cache. A plugin
    that does not define on_event is silently skipped.
    """
    from .project import Project
    from .models import Artifact

    assert isinstance(project, Project)
    assert isinstance(artifact, Artifact)

    if project._plugin_cache is None:
        project._plugin_cache = load_plugins(project.root)

    for mod in project._plugin_cache:
        handler = getattr(mod, "on_event", None)
        if handler is None:
            continue
        try:
            handler(event, artifact, project)
        except Exception as exc:
            print(f"Plugin {mod.__spec__.origin} error: {exc}", file=sys.stderr)
