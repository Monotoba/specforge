"""Bulk artifact operations for SpecForge.

Filters a project's artifact list and applies a single action to all matches.
Supports dry-run mode — returns the affected list without writing.
"""
from __future__ import annotations

from specforge_core.models import Artifact, ArtifactKind, ArtifactStatus
from specforge_core.project import Project


def bulk_update(
    project: Project,
    action: str,
    filters: dict,
    params: dict,
    dry_run: bool = False,
) -> list[Artifact]:
    """Apply action to all artifacts matching filters.

    Args:
        project:  The project to operate on.
        action:   One of 'update-status', 'archive', 'tag-add', 'tag-remove'.
        filters:  Dict with optional keys 'kind' (list[str]), 'status' (str), 'tag' (list[str]).
        params:   Action-specific params ('to_status', 'tags').
        dry_run:  If True, return matches without writing.

    Returns:
        List of Artifact objects that were (or would be) affected.
    """
    artifacts = project.artifacts()
    matched = _filter(artifacts, filters)

    if dry_run or not matched:
        return matched

    if action == "update-status":
        new_status = ArtifactStatus(params["to_status"])
        for a in matched:
            project.update_status(a.id, new_status)

    elif action == "archive":
        for a in matched:
            project.update_status(a.id, ArtifactStatus.ARCHIVED)

    elif action == "tag-add":
        tags_to_add = params.get("tags", [])
        for a in matched:
            project.link_artifact(a.id, tags=tags_to_add)

    elif action == "tag-remove":
        tags_to_remove = params.get("tags", [])
        for a in matched:
            project.unlink_artifact(a.id, tags=tags_to_remove)

    else:
        raise ValueError(f"Unknown bulk action: {action!r}. Use 'update-status', 'archive', 'tag-add', or 'tag-remove'.")

    return matched


def _filter(artifacts: list[Artifact], filters: dict) -> list[Artifact]:
    """Return artifacts matching all supplied filters."""
    result = artifacts

    if kinds := filters.get("kind"):
        kind_enums = {ArtifactKind(k) for k in kinds}
        result = [a for a in result if a.kind in kind_enums]

    if status := filters.get("status"):
        status_enum = ArtifactStatus(status)
        result = [a for a in result if a.status == status_enum]

    if tags := filters.get("tag"):
        tag_set = set(tags)
        result = [a for a in result if tag_set.issubset(set(a.tags))]

    return result
