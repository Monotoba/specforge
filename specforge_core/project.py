from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import ProjectConfig, load_config
from .idgen import ID_RE
from .markdown import read_artifact, write_artifact
from .models import Artifact, ArtifactKind, ArtifactStatus
from .plugins import fire_plugin_event
from .webhooks import fire_event

DIR_BY_KIND = {
    ArtifactKind.IDEA: "exploration/idea-log",
    ArtifactKind.CANDIDATE: "incubation/candidates",
    ArtifactKind.REQUIREMENT: "specification/requirements",
    ArtifactKind.DECISION: "specification/decisions",
    ArtifactKind.ASSUMPTION: "specification/assumptions",
    ArtifactKind.CONSTRAINT: "specification/constraints",
    ArtifactKind.CHANGE_ORDER: "change-orders/proposed",
    ArtifactKind.TASK: "development/work-log/tasks",
    ArtifactKind.TEST: "development/test-logs/tests",
    ArtifactKind.VERIFICATION: "development/verification-logs/verifications",
    ArtifactKind.REFERENCE: "exploration/references",
    ArtifactKind.CONVERSATION: "conversation-vault/sessions",
    ArtifactKind.WORK_LOG: "development/work-log/entries",
    ArtifactKind.CHANGELOG: "development/changelog",
    ArtifactKind.TEST_LOG: "development/test-logs/runs",
    ArtifactKind.VERIFICATION_LOG: "development/verification-logs/runs",
}

ROOT_DIRS = [
    "exploration/idea-log",
    "exploration/references",
    "incubation/candidates",
    "incubation/investigations",
    "incubation/evaluations",
    "specification/requirements",
    "specification/decisions",
    "specification/assumptions",
    "specification/constraints",
    "specification/interfaces",
    "specification/acceptance",
    "change-orders/proposed",
    "change-orders/approved",
    "change-orders/rejected",
    "change-orders/archived",
    "development/work-log/entries",
    "development/work-log/tasks",
    "development/changelog",
    "development/test-logs/runs",
    "development/test-logs/tests",
    "development/verification-logs/runs",
    "development/verification-logs/verifications",
    "conversation-vault/sessions",
    "conversation-vault/summaries",
    "conversation-vault/extracted-decisions",
    "trace/exports",
]


class Project:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self._artifact_cache: list[Artifact] = []
        self._cache_snapshot: dict[Path, float] = {}
        self._config: ProjectConfig | None = None
        self._plugin_cache: list | None = None

    @property
    def config(self) -> ProjectConfig:
        if self._config is None:
            self._config = load_config(self.root)
        return self._config

    def reload_config(self) -> ProjectConfig:
        self._config = load_config(self.root)
        return self._config

    def init(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for rel in ROOT_DIRS:
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        memory = self.root / "exploration" / "memory.md"
        if not memory.exists():
            memory.write_text(
                "# Exploration Memory\n\nLong-term notes, vocabulary, project background, rejected directions, and recurring references.\n",
                encoding="utf-8",
            )
        incubation = self.root / "incubation" / "memory.md"
        if not incubation.exists():
            incubation.write_text(
                "# Incubation Memory\n\nStructured notes about candidate features, investigations, tradeoffs, and unresolved questions.\n",
                encoding="utf-8",
            )
        specmem = self.root / "specification" / "memory.md"
        if not specmem.exists():
            specmem.write_text(
                "# Specification Memory\n\nAuthoritative requirements, decisions, assumptions, constraints, links, and acceptance policy live here.\n",
                encoding="utf-8",
            )
        plugin_dir = self.root / ".specforge" / "plugins"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        example = plugin_dir / "example_plugin.py.disabled"
        if not example.exists():
            from .plugins import _EXAMPLE_PLUGIN
            example.write_text(_EXAMPLE_PLUGIN, encoding="utf-8")
        template_dir = self.root / ".specforge" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        from .templates import _BUILTIN_TEMPLATES
        for kind_name, body in _BUILTIN_TEMPLATES.items():
            tfile = template_dir / f"{kind_name}.md"
            if not tfile.exists():
                tfile.write_text(body, encoding="utf-8")
        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("trace/traceability.sqlite\n.venv/\n__pycache__/\n", encoding="utf-8")

    def create_artifact(
        self,
        kind: ArtifactKind,
        title: str,
        body: str,
        status: ArtifactStatus = ArtifactStatus.DRAFT,
        git_commit: bool = False,
        **links: list[str] | str | None,
    ) -> Artifact:
        artifact_id = self._next_id(kind)
        now = datetime.now(timezone.utc)
        artifact = Artifact(
            id=artifact_id,
            kind=kind,
            title=title,
            status=status,
            created_at=now,
            updated_at=now,
            body=body,
            **{k: v for k, v in links.items() if v is not None},
        )
        folder = self.root / DIR_BY_KIND[kind]
        filename = f"{artifact.id}-{slugify(title)}.md"
        artifact.path = folder / filename
        write_artifact(artifact.path, artifact)
        self.invalidate_cache()
        if git_commit:
            from .gitwrap import commit_artifact
            commit_artifact(self.root, artifact.path, f"Add {artifact.id}: {artifact.title}")
        fire_event(self, "artifact.created", artifact)
        fire_plugin_event(self, "artifact.created", artifact)
        return artifact

    def artifacts(self) -> list[Artifact]:
        snapshot = {
            p: p.stat().st_mtime
            for p in self.root.rglob("*.md")
        }
        if snapshot == self._cache_snapshot and self._artifact_cache:
            return self._artifact_cache
        result: list[Artifact] = []
        for path in snapshot:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if text.startswith("---") and "kind:" in text and "id:" in text:
                    result.append(read_artifact(path))
            except Exception:
                continue
        result.sort(key=lambda item: item.id)
        self._cache_snapshot = snapshot
        self._artifact_cache = result
        return result

    def _next_id(self, kind: ArtifactKind) -> str:
        """Derive the next artifact ID using the cached artifact list (avoids extra rglob scan)."""
        from .models import PREFIX_BY_KIND
        prefix = PREFIX_BY_KIND[kind]
        max_seen = 0
        for artifact in self.artifacts():
            m = ID_RE.match(artifact.id)
            if m and m.group(1) == prefix:
                max_seen = max(max_seen, int(m.group(2)))
        # Fall back to filesystem scan if cache is empty (first artifact in project)
        if max_seen == 0:
            for path in self.root.rglob("*.md"):
                m2 = ID_RE.search(path.name)
                if m2 and m2.group(1) == prefix:
                    max_seen = max(max_seen, int(m2.group(2)))
        return f"{prefix}-{max_seen + 1:04d}"

    def invalidate_cache(self) -> None:
        """Force the next artifacts() call to re-scan the filesystem."""
        self._cache_snapshot = {}
        self._artifact_cache = []

    def get_artifact(self, artifact_id: str) -> Artifact:
        for artifact in self.artifacts():
            if artifact.id == artifact_id.upper():
                return artifact
        raise KeyError(artifact_id)

    def update_status(
        self, artifact_id: str, new_status: ArtifactStatus, git_commit: bool = False
    ) -> Artifact:
        artifact = self.get_artifact(artifact_id)
        artifact.status = new_status
        artifact.updated_at = datetime.now(timezone.utc)
        assert artifact.path is not None
        write_artifact(artifact.path, artifact)
        self.invalidate_cache()
        if git_commit:
            from .gitwrap import commit_artifact
            commit_artifact(
                self.root, artifact.path,
                f"Update {artifact.id} status: {new_status.value}",
            )
        fire_event(self, "artifact.status_changed", artifact)
        fire_plugin_event(self, "artifact.status_changed", artifact)
        return artifact

    def unlink_artifact(
        self,
        artifact_id: str,
        clear_source: bool = False,
        git_commit: bool = False,
        **removals: list[str] | None,
    ) -> Artifact:
        """Remove specific values from list link fields. Pass clear_source=True to clear source."""
        artifact = self.get_artifact(artifact_id)
        _list_fields = {
            "implements", "related_requirements", "related_decisions",
            "related_assumptions", "depends_on", "dependents",
            "verified_by", "references", "tags",
        }
        for field, value in removals.items():
            if value is None:
                continue
            if field in _list_fields:
                remove_set = set(value)
                current: list[str] = list(getattr(artifact, field, []))
                setattr(artifact, field, [v for v in current if v not in remove_set])
        if clear_source:
            artifact.source = None
        artifact.updated_at = datetime.now(timezone.utc)
        assert artifact.path is not None
        write_artifact(artifact.path, artifact)
        self.invalidate_cache()
        if git_commit:
            from .gitwrap import commit_artifact
            commit_artifact(self.root, artifact.path, f"Unlink {artifact.id}: {artifact.title}")
        fire_event(self, "artifact.unlinked", artifact)
        fire_plugin_event(self, "artifact.unlinked", artifact)
        return artifact

    def link_artifact(
        self,
        artifact_id: str,
        git_commit: bool = False,
        **updates: list[str] | str | None,
    ) -> Artifact:
        """Append links to an existing artifact. List fields are merged (no duplicates).
        Passing source replaces the existing source. None values are skipped."""
        artifact = self.get_artifact(artifact_id)
        _list_fields = {
            "implements", "related_requirements", "related_decisions",
            "related_assumptions", "depends_on", "dependents",
            "verified_by", "references", "tags",
        }
        for field, value in updates.items():
            if value is None:
                continue
            if field == "source":
                artifact.source = str(value)
            elif field in _list_fields:
                current: list[str] = list(getattr(artifact, field, []))
                new_vals: list[str] = [str(value)] if isinstance(value, str) else list(value)  # type: ignore[arg-type]
                for v in new_vals:
                    if v not in current:
                        current.append(v)
                setattr(artifact, field, current)
        artifact.updated_at = datetime.now(timezone.utc)
        assert artifact.path is not None
        write_artifact(artifact.path, artifact)
        self.invalidate_cache()
        if git_commit:
            from .gitwrap import commit_artifact
            commit_artifact(self.root, artifact.path, f"Link {artifact.id}: {artifact.title}")
        fire_event(self, "artifact.linked", artifact)
        fire_plugin_event(self, "artifact.linked", artifact)
        return artifact

    def promote_artifact(
        self,
        artifact_id: str,
        target_kind: ArtifactKind,
        title: str | None = None,
        body: str | None = None,
        git_commit: bool = False,
        **links: list[str] | str | None,
    ) -> Artifact:
        source = self.get_artifact(artifact_id)
        default_status = _DEFAULT_STATUS_BY_KIND.get(target_kind, ArtifactStatus.DRAFT)
        promoted = self.create_artifact(
            target_kind,
            title or source.title,
            body or source.body,
            status=default_status,
            source=source.id,
            **links,
        )
        if git_commit and promoted.path:
            from .gitwrap import commit_artifact
            commit_artifact(
                self.root, promoted.path,
                f"Promote {artifact_id} → {promoted.id}: {promoted.title}",
            )
        fire_event(self, "artifact.promoted", promoted)
        fire_plugin_event(self, "artifact.promoted", promoted)
        return promoted


_DEFAULT_STATUS_BY_KIND: dict[ArtifactKind, ArtifactStatus] = {
    ArtifactKind.IDEA: ArtifactStatus.DRAFT,
    ArtifactKind.CANDIDATE: ArtifactStatus.PROPOSED,
    ArtifactKind.REQUIREMENT: ArtifactStatus.APPROVED,
    ArtifactKind.DECISION: ArtifactStatus.APPROVED,
    ArtifactKind.ASSUMPTION: ArtifactStatus.APPROVED,
    ArtifactKind.CONSTRAINT: ArtifactStatus.APPROVED,
    ArtifactKind.CHANGE_ORDER: ArtifactStatus.PROPOSED,
    ArtifactKind.TASK: ArtifactStatus.DRAFT,
    ArtifactKind.TEST: ArtifactStatus.DRAFT,
    ArtifactKind.VERIFICATION: ArtifactStatus.DRAFT,
}


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned[:60] or "artifact"
