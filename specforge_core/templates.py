"""Artifact template loader for SpecForge.

Templates live in .specforge/templates/<kind>.md and may contain optional
YAML front matter (tags, status overrides) followed by a Markdown body stub.
"""
from __future__ import annotations

from pathlib import Path

import yaml

TEMPLATES_DIR = ".specforge/templates"

_REQUIREMENT_TEMPLATE = """\
---
tags: []
---

## Purpose

<!-- What requirement this satisfies and why it matters -->

## Acceptance criteria

- [ ]
"""

_TASK_TEMPLATE = """\
---
tags: []
---

## What

<!-- A concise description of the work to be done -->

## Done when

- [ ]
"""

_TEST_TEMPLATE = """\
---
tags: []
---

## Test objective

<!-- What behaviour is being verified -->

## Steps

1.
2.

## Expected result

<!-- Pass/fail criteria -->
"""

_BUILTIN_TEMPLATES = {
    "requirement": _REQUIREMENT_TEMPLATE,
    "task": _TASK_TEMPLATE,
    "test": _TEST_TEMPLATE,
}


def load_template(root: Path, kind: str) -> tuple[str, dict]:
    """Load template body and metadata for the given artifact kind.

    Returns (body, metadata) where metadata may include 'tags', 'status', etc.
    Returns ("", {}) if no template exists for this kind.
    """
    template_path = root / TEMPLATES_DIR / f"{kind}.md"
    if not template_path.exists():
        return "", {}

    text = template_path.read_text(encoding="utf-8")
    if not text.strip():
        return "", {}

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1]) or {}
            except Exception:
                metadata = {}
            body = parts[2].strip()
            return body, metadata if isinstance(metadata, dict) else {}
    return text.strip(), {}


def list_templates(root: Path) -> list[str]:
    """Return kind names for which a template file exists."""
    template_dir = root / TEMPLATES_DIR
    if not template_dir.is_dir():
        return []
    return [p.stem for p in sorted(template_dir.glob("*.md"))]
