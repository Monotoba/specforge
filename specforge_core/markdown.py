from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .models import Artifact, ArtifactKind, ArtifactStatus


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"cannot parse datetime from {value!r}")


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("artifact file does not start with YAML front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("artifact file has no closing YAML front matter marker")
    metadata_text = text[4:end]
    body = text[end + 5 :]
    metadata = yaml.safe_load(metadata_text) or {}
    if not isinstance(metadata, dict):
        raise ValueError("artifact front matter must be a mapping")
    return metadata, body


def read_artifact(path: Path) -> Artifact:
    meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    meta["kind"] = ArtifactKind(meta["kind"])
    meta["status"] = ArtifactStatus(meta.get("status", "draft"))
    if "created_at" in meta:
        meta["created_at"] = _parse_datetime(meta["created_at"])
    if "updated_at" in meta:
        meta["updated_at"] = _parse_datetime(meta["updated_at"])
    return Artifact(**meta, body=body, path=path)


def write_artifact(path: Path, artifact: Artifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(artifact.to_frontmatter(), sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{front}---\n{artifact.body}", encoding="utf-8")
