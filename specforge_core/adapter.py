"""AI adapter — structured tool-call dispatch for Claude Code, PocketFlow, and other agents.

Agents call handle_tool_call(project, call) with a dict describing the action.
All mutations go through Project methods, never by writing files directly.

Supported actions
-----------------
create_artifact   kind, title, body, [status, source, tags, implements,
                  related_requirements, depends_on, verified_by, git_commit]
promote_artifact  id, target_kind, [title, body, git_commit]
update_status     id, status, [git_commit]
get_artifact      id
list_artifacts    [kind, status, tag]
search            query, [kinds, statuses, tags]
context_pack      —
report            —
validate          —
"""
from __future__ import annotations

from .models import ArtifactKind, ArtifactStatus
from .project import Project
from .search import search_artifacts
from .trace import TraceIndex
from .validation import validate_project


def handle_tool_call(project: Project, call: dict[str, object]) -> dict[str, object]:
    """Dispatch a tool call and return a result dict.

    Always returns {"ok": bool, "result": ..., "error": str | None}.
    Never raises — errors are returned in the result dict.
    """
    action = str(call.get("action", ""))
    try:
        result = _dispatch(project, action, call)
        return {"ok": True, "result": result, "error": None}
    except Exception as exc:
        return {"ok": False, "result": None, "error": str(exc)}


def _dispatch(project: Project, action: str, call: dict[str, object]) -> object:
    if action == "link_artifact":
        return _link(project, call)
    if action == "unlink_artifact":
        return _unlink(project, call)
    if action == "create_artifact":
        return _create(project, call)
    if action == "promote_artifact":
        return _promote(project, call)
    if action == "update_status":
        return _update_status(project, call)
    if action == "get_artifact":
        artifact = project.get_artifact(str(call["id"]))
        return _artifact_summary(artifact, project)
    if action == "list_artifacts":
        return _list(project, call)
    if action == "search":
        return _search(project, call)
    if action == "context_pack":
        from .contextpack import build_context_pack
        return build_context_pack(project)
    if action == "report":
        from .report import build_acceptance_report
        index = TraceIndex(project)
        index.rebuild()
        return build_acceptance_report(project, index)
    if action == "validate":
        errors = validate_project(project)
        return {"ok": not errors, "errors": errors}
    raise ValueError(f"Unknown action: {action!r}")


def _unlink(project: Project, call: dict[str, object]) -> object:
    artifact = project.unlink_artifact(
        str(call["id"]),
        clear_source=bool(call.get("clear_source", False)),
        git_commit=bool(call.get("git_commit", False)),
        **{k: v for k, v in call.items()
           if k not in ("action", "id", "clear_source", "git_commit") and v is not None},  # type: ignore[arg-type]
    )
    return _artifact_summary(artifact, project)


def _link(project: Project, call: dict[str, object]) -> object:
    artifact = project.link_artifact(
        str(call["id"]),
        git_commit=bool(call.get("git_commit", False)),
        **{k: v for k, v in call.items()
           if k not in ("action", "id", "git_commit") and v is not None},  # type: ignore[arg-type]
    )
    return _artifact_summary(artifact, project)


def _create(project: Project, call: dict[str, object]) -> object:
    kind = ArtifactKind(str(call["kind"]))
    title = str(call["title"])
    body = str(call.get("body", ""))
    status_val = call.get("status")
    status = ArtifactStatus(str(status_val)) if status_val else None
    kwargs: dict[str, object] = {}
    for field in ("source", "depends_on", "implements", "related_requirements",
                  "references", "verified_by", "tags"):
        if field in call:
            kwargs[field] = call[field]
    if status:
        kwargs["status"] = status
    if call.get("git_commit"):
        kwargs["git_commit"] = True
    artifact = project.create_artifact(kind, title, body, **kwargs)  # type: ignore[arg-type]
    return _artifact_summary(artifact, project)


def _promote(project: Project, call: dict[str, object]) -> object:
    artifact_id = str(call["id"])
    target_kind = ArtifactKind(str(call["target_kind"]))
    promoted = project.promote_artifact(
        artifact_id,
        target_kind,
        title=str(call["title"]) if "title" in call else None,
        body=str(call["body"]) if "body" in call else None,
        git_commit=bool(call.get("git_commit", False)),
    )
    return _artifact_summary(promoted, project)


def _update_status(project: Project, call: dict[str, object]) -> object:
    artifact = project.update_status(
        str(call["id"]),
        ArtifactStatus(str(call["status"])),
        git_commit=bool(call.get("git_commit", False)),
    )
    return _artifact_summary(artifact, project)


def _list(project: Project, call: dict[str, object]) -> object:
    artifacts = project.artifacts()
    kind_filter = call.get("kind")
    status_filter = call.get("status")
    tag_filter = call.get("tag")
    result = []
    for a in artifacts:
        if kind_filter and a.kind.value != str(kind_filter):
            continue
        if status_filter and a.status.value != str(status_filter):
            continue
        if tag_filter and str(tag_filter) not in a.tags:
            continue
        result.append(_artifact_summary(a, project))
    return result


def _search(project: Project, call: dict[str, object]) -> object:
    query = str(call.get("query", ""))
    kinds_raw = call.get("kinds")
    kinds = [ArtifactKind(k) for k in kinds_raw] if isinstance(kinds_raw, list) else None
    statuses_raw = call.get("statuses")
    statuses = [ArtifactStatus(s) for s in statuses_raw] if isinstance(statuses_raw, list) else None
    tags_raw = call.get("tags")
    tags = list(tags_raw) if isinstance(tags_raw, list) else None
    return search_artifacts(project, query, kinds=kinds, statuses=statuses, tags=tags)


def _artifact_summary(artifact: object, project: Project) -> dict[str, object]:
    from .models import Artifact
    assert isinstance(artifact, Artifact)
    return {
        "id": artifact.id,
        "kind": artifact.kind.value,
        "status": artifact.status.value,
        "title": artifact.title,
        "body": artifact.body,
        "source": artifact.source,
        "tags": artifact.tags,
        "implements": artifact.implements,
        "related_requirements": artifact.related_requirements,
        "verified_by": artifact.verified_by,
        "depends_on": artifact.depends_on,
        "path": str(artifact.path.relative_to(project.root) if artifact.path else ""),
    }
