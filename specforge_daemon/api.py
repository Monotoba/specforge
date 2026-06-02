from __future__ import annotations

from pathlib import Path
from typing import Optional

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from specforge_core.adapter import handle_tool_call
from specforge_core.config import load_config, save_config
from specforge_core.contextpack import build_context_pack
from specforge_core.status import project_status
from specforge_core.export import ExportFormat, export_project, build_matrix, to_csv, to_markdown
from specforge_core.gitwrap import artifact_log
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.report import build_acceptance_report
from specforge_core.search import search_artifacts
from specforge_core.trace import TraceIndex
from specforge_core.validation import validate_project
from specforge_core.webhooks import WebhookEntry
from specforge_daemon.watcher import ProjectWatcher

_active_project: Project | None = None
_watcher: ProjectWatcher | None = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    yield
    if _watcher is not None:
        _watcher.stop()


app = FastAPI(title="SpecForge Daemon", version="0.1.0", lifespan=lifespan)


class OpenProjectRequest(BaseModel):
    path: str


class CreateArtifactRequest(BaseModel):
    kind: ArtifactKind
    title: str
    body: str
    status: ArtifactStatus = ArtifactStatus.DRAFT
    source: Optional[str] = None
    depends_on: list[str] = []
    implements: list[str] = []
    related_requirements: list[str] = []
    references: list[str] = []
    verified_by: list[str] = []
    tags: list[str] = []
    git_commit: bool = False


class PromoteRequest(BaseModel):
    target_kind: ArtifactKind
    title: Optional[str] = None
    body: Optional[str] = None
    git_commit: bool = False


class UpdateStatusRequest(BaseModel):
    status: ArtifactStatus
    git_commit: bool = False


class LinkArtifactRequest(BaseModel):
    implements: list[str] = []
    related_requirements: list[str] = []
    verified_by: list[str] = []
    depends_on: list[str] = []
    source: Optional[str] = None
    tags: list[str] = []
    git_commit: bool = False


class UnlinkArtifactRequest(BaseModel):
    implements: list[str] = []
    related_requirements: list[str] = []
    verified_by: list[str] = []
    depends_on: list[str] = []
    tags: list[str] = []
    clear_source: bool = False
    git_commit: bool = False


class WebhookEntryRequest(BaseModel):
    url: str
    events: list[str] = []
    secret: str = ""


class DraftArtifactRequest(BaseModel):
    kind: str
    prompt: str
    title: Optional[str] = None
    tags: list[str] = []
    git_commit: bool = False


def active_project() -> Project:
    if _active_project is None:
        raise HTTPException(status_code=400, detail="No active project. Call /projects/open first.")
    return _active_project


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "specforge-daemon", "status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
def ui() -> str:
    html_path = Path(__file__).resolve().parent.parent / "specforge_web" / "index.html"
    return html_path.read_text(encoding="utf-8")


_HELP_DIR = Path(__file__).resolve().parent.parent / "specforge_web" / "help"

_HELP_TOPICS = {
    "getting_started": "GETTING_STARTED.md",
    "workflow":        "WORKFLOW.md",
    "artifacts":       "ARTIFACTS.md",
    "user_manual":     "USER_MANUAL.md",
    "configuration":   "CONFIGURATION.md",
    "web_ui":          "WEB_UI.md",
    "studio":          "STUDIO.md",
    "ai_drafting":     "AI_DRAFTING.md",
    "webhooks":        "WEBHOOKS.md",
    "plugins":         "PLUGINS.md",
    "templates":       "TEMPLATES.md",
    "mcp":             "MCP.md",
    "troubleshooting": "TROUBLESHOOTING.md",
}


@app.get("/help/{topic}")
def help_topic(topic: str) -> dict[str, str]:
    """Return the markdown content for a help topic."""
    filename = _HELP_TOPICS.get(topic.lower())
    if not filename:
        raise HTTPException(status_code=404, detail=f"Unknown help topic: {topic!r}. "
                            f"Available: {', '.join(_HELP_TOPICS)}")
    path = _HELP_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Help file missing: {filename}")
    return {"topic": topic, "markdown": path.read_text(encoding="utf-8")}


@app.get("/help")
def help_index() -> dict[str, list[str]]:
    """List available help topics."""
    return {"topics": list(_HELP_TOPICS.keys())}


@app.post("/projects/open")
def open_project(request: OpenProjectRequest) -> dict[str, str]:
    global _active_project, _watcher
    if _watcher is not None:
        _watcher.stop()
    project = Project(request.path)
    project.init()
    _active_project = project
    new_watcher = ProjectWatcher(project)
    new_watcher.start()
    _watcher = new_watcher
    return {"path": str(project.root)}


@app.get("/artifacts")
def list_artifacts(kind: ArtifactKind | None = None) -> list[dict[str, object]]:
    project = active_project()
    result = []
    for artifact in project.artifacts():
        if kind and artifact.kind != kind:
            continue
        data = artifact.model_dump(exclude={"body"})
        data["kind"] = artifact.kind.value
        data["status"] = artifact.status.value
        data["path"] = str(artifact.path.relative_to(project.root) if artifact.path else "")
        result.append(data)
    return result


@app.post("/artifacts")
def create_artifact(request: CreateArtifactRequest) -> dict[str, object]:
    project = active_project()
    artifact = project.create_artifact(
        request.kind,
        request.title,
        request.body,
        status=request.status,
        git_commit=request.git_commit,
        source=request.source,
        depends_on=request.depends_on,
        implements=request.implements,
        related_requirements=request.related_requirements,
        references=request.references,
        verified_by=request.verified_by,
        tags=request.tags,
    )
    rel_path = artifact.path.relative_to(project.root) if artifact.path else ""
    return {"id": artifact.id, "path": str(rel_path)}


@app.post("/trace/rebuild")
def rebuild_trace() -> dict[str, object]:
    project = active_project()
    index = TraceIndex(project)
    index.rebuild()
    return {"db_path": str(index.db_path), "unverified_requirements": index.unverified_requirements()}


@app.get("/trace/{artifact_id}")
def trace_artifact(artifact_id: str) -> dict[str, object]:
    project = active_project()
    index = TraceIndex(project)
    try:
        return index.artifact_graph(artifact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc


@app.post("/artifacts/{artifact_id}/unlink")
def unlink_artifact(artifact_id: str, request: UnlinkArtifactRequest) -> dict[str, object]:
    project = active_project()
    try:
        artifact = project.unlink_artifact(
            artifact_id,
            clear_source=request.clear_source,
            git_commit=request.git_commit,
            implements=request.implements or None,
            related_requirements=request.related_requirements or None,
            verified_by=request.verified_by or None,
            depends_on=request.depends_on or None,
            tags=request.tags or None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc
    return {"id": artifact.id, "title": artifact.title}


@app.post("/artifacts/{artifact_id}/link")
def link_artifact(artifact_id: str, request: LinkArtifactRequest) -> dict[str, object]:
    project = active_project()
    try:
        artifact = project.link_artifact(
            artifact_id,
            git_commit=request.git_commit,
            implements=request.implements or None,
            related_requirements=request.related_requirements or None,
            verified_by=request.verified_by or None,
            depends_on=request.depends_on or None,
            source=request.source,
            tags=request.tags or None,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc
    return {"id": artifact.id, "title": artifact.title}


@app.post("/artifacts/{artifact_id}/promote")
def promote_artifact(artifact_id: str, request: PromoteRequest) -> dict[str, object]:
    project = active_project()
    try:
        promoted = project.promote_artifact(
            artifact_id, request.target_kind,
            title=request.title, body=request.body, git_commit=request.git_commit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc
    promoted_path = promoted.path.relative_to(project.root) if promoted.path else ""
    return {"id": promoted.id, "path": str(promoted_path)}


@app.patch("/artifacts/{artifact_id}/status")
def update_artifact_status(artifact_id: str, request: UpdateStatusRequest) -> dict[str, object]:
    project = active_project()
    try:
        artifact = project.update_status(artifact_id, request.status, git_commit=request.git_commit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc
    return {"id": artifact.id, "status": artifact.status.value}


@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str) -> dict[str, object]:
    project = active_project()
    try:
        artifact = project.get_artifact(artifact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc
    data = artifact.model_dump()
    data["kind"] = artifact.kind.value
    data["status"] = artifact.status.value
    data["path"] = str(artifact.path.relative_to(project.root) if artifact.path else "")
    return data


@app.get("/context-pack")
def context_pack() -> dict[str, object]:
    project = active_project()
    return build_context_pack(project)


@app.get("/report", response_class=HTMLResponse)
def acceptance_report() -> str:
    project = active_project()
    index = TraceIndex(project)
    index.rebuild()
    return build_acceptance_report(project, index)


@app.get("/export")
def export_matrix(fmt: ExportFormat = ExportFormat.BOTH) -> dict[str, object]:
    project = active_project()
    written = export_project(project, fmt)
    return {k: str(v.relative_to(project.root)) for k, v in written.items()}


@app.get("/export/matrix")
def export_matrix_inline(fmt: str = "markdown") -> object:
    project = active_project()
    rows = build_matrix(project)
    if fmt == "csv":
        return to_csv(rows)
    return to_markdown(rows)


@app.get("/search")
def search(
    q: str,
    kind: list[ArtifactKind] = [],  # noqa: B006
    status: list[ArtifactStatus] = [],  # noqa: B006
    tag: list[str] = [],  # noqa: B006
) -> list[dict[str, object]]:
    project = active_project()
    return search_artifacts(
        project,
        q,
        kinds=kind or None,
        statuses=status or None,
        tags=tag or None,
    )


@app.get("/status")
def get_status() -> dict[str, object]:
    project = active_project()
    return project_status(project)


@app.post("/tool-call")
def tool_call(call: dict[str, object]) -> dict[str, object]:
    """AI adapter entry point — dispatch a structured tool-call dict."""
    project = active_project()
    return handle_tool_call(project, call)


@app.get("/git/log")
def git_log(n: int = 20) -> list[dict[str, str]]:
    project = active_project()
    return artifact_log(project.root, max_count=n)


@app.get("/validate")
def validate() -> dict[str, object]:
    project = active_project()
    errors = validate_project(project)
    return {"ok": not errors, "errors": errors}


@app.post("/draft")
def draft_artifact(request: DraftArtifactRequest) -> dict[str, object]:
    """Generate an artifact body with the configured LLM and create it."""
    from specforge_core.llm import LLMError, _DRAFT_SYSTEM, complete_with_fallback
    from specforge_core.models import ArtifactKind

    project = active_project()
    try:
        artifact_kind = ArtifactKind(request.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown kind: {request.kind!r}")

    system = _DRAFT_SYSTEM + f"\n\nArtifact kind: {artifact_kind.value}"
    title = request.title or (request.prompt[:60].rstrip() + ("…" if len(request.prompt) > 60 else ""))

    try:
        body = complete_with_fallback(
            request.prompt, system, project.config.llm,
            ask_fallback=lambda msg: False,  # no interactive fallback in REST mode
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    git_commit = request.git_commit or project.config.git_commit
    artifact = project.create_artifact(
        artifact_kind, title, body,
        git_commit=git_commit,
        tags=request.tags or None,
    )
    return {
        "id": artifact.id,
        "kind": artifact.kind.value,
        "title": artifact.title,
        "status": artifact.status.value,
        "body": artifact.body,
        "tags": artifact.tags,
        "path": str(artifact.path) if artifact.path else None,
    }


@app.get("/webhooks")
def list_webhooks() -> list[dict[str, object]]:
    project = active_project()
    cfg = load_config(project.root)
    return [
        {"url": e.url, "events": e.events, "secret": bool(e.secret)}
        for e in cfg.webhooks
    ]


@app.post("/webhooks")
def add_webhook(request: WebhookEntryRequest) -> dict[str, str]:
    project = active_project()
    cfg = load_config(project.root)
    entry = WebhookEntry(url=request.url, events=request.events, secret=request.secret)
    cfg.webhooks.append(entry)
    save_config(project.root, cfg)
    project.reload_config()
    return {"ok": "Webhook added", "url": request.url}


@app.delete("/webhooks")
def remove_webhook(url: str = Query(...)) -> dict[str, str]:
    project = active_project()
    cfg = load_config(project.root)
    original_count = len(cfg.webhooks)
    cfg.webhooks = [e for e in cfg.webhooks if e.url != url]
    if len(cfg.webhooks) < original_count:
        save_config(project.root, cfg)
        project.reload_config()
        return {"ok": "Webhook removed", "url": url}
    else:
        raise HTTPException(status_code=404, detail=f"Webhook not found: {url}")
