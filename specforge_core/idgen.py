from __future__ import annotations

import re
from pathlib import Path

from .models import ArtifactKind, PREFIX_BY_KIND

ID_RE = re.compile(r"([A-Z]+)-(\d{4})")


def next_id(root: Path, kind: ArtifactKind) -> str:
    prefix = PREFIX_BY_KIND[kind]
    max_seen = 0
    for path in root.rglob("*.md"):
        match = ID_RE.search(path.name)
        if match and match.group(1) == prefix:
            max_seen = max(max_seen, int(match.group(2)))
    return f"{prefix}-{max_seen + 1:04d}"
