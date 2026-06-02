from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Artifact
from .project import Project

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source TEXT
);
CREATE TABLE IF NOT EXISTS links (
  src_id TEXT NOT NULL,
  dst_id TEXT NOT NULL,
  link_type TEXT NOT NULL,
  PRIMARY KEY (src_id, dst_id, link_type)
);
CREATE TABLE IF NOT EXISTS bodies (
  id TEXT PRIMARY KEY,
  body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tags (
  artifact_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (artifact_id, tag)
);
"""

LINK_FIELDS = {
    "depends_on": "depends_on",
    "dependents": "dependent",
    "related_requirements": "related_requirement",
    "related_decisions": "related_decision",
    "related_assumptions": "related_assumption",
    "references": "reference",
    "verified_by": "verified_by",
    "implements": "implements",
}


class TraceIndex:
    def __init__(self, project: Project):
        self.project = project
        self.db_path = project.root / "trace" / "traceability.sqlite"

    def rebuild(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=15) as conn:
            conn.executescript(SCHEMA)
            conn.execute("DELETE FROM artifacts")
            conn.execute("DELETE FROM links")
            conn.execute("DELETE FROM bodies")
            conn.execute("DELETE FROM tags")
            for artifact in self.project.artifacts():
                self._insert_artifact(conn, artifact)
            conn.commit()

    def _insert_artifact(self, conn: sqlite3.Connection, artifact: Artifact) -> None:
        conn.execute(
            """
            INSERT INTO artifacts(id, kind, title, status, path, created_at, updated_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.id,
                artifact.kind.value,
                artifact.title,
                artifact.status.value,
                str(artifact.path.relative_to(self.project.root) if artifact.path else ""),
                artifact.created_at.isoformat(),
                artifact.updated_at.isoformat(),
                artifact.source,
            ),
        )
        conn.execute("INSERT INTO bodies(id, body) VALUES (?, ?)", (artifact.id, artifact.body))
        for field, link_type in LINK_FIELDS.items():
            values = getattr(artifact, field)
            for dst in values:
                conn.execute(
                    "INSERT OR IGNORE INTO links(src_id, dst_id, link_type) VALUES (?, ?, ?)",
                    (artifact.id, dst, link_type),
                )
        if artifact.source:
            conn.execute(
                "INSERT OR IGNORE INTO links(src_id, dst_id, link_type) VALUES (?, ?, ?)",
                (artifact.id, artifact.source, "source"),
            )
        for tag in artifact.tags:
            conn.execute(
                "INSERT OR IGNORE INTO tags(artifact_id, tag) VALUES (?, ?)",
                (artifact.id, tag),
            )

    def artifact_graph(self, artifact_id: str) -> dict[str, object]:
        if not self.db_path.exists():
            self.rebuild()
        with sqlite3.connect(self.db_path, timeout=15) as conn:
            conn.row_factory = sqlite3.Row
            artifact = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
            if artifact is None:
                raise KeyError(artifact_id)
            outgoing = conn.execute(
                "SELECT dst_id, link_type FROM links WHERE src_id = ? ORDER BY link_type, dst_id",
                (artifact_id,),
            ).fetchall()
            incoming = conn.execute(
                "SELECT src_id, link_type FROM links WHERE dst_id = ? ORDER BY link_type, src_id",
                (artifact_id,),
            ).fetchall()
        return {
            "artifact": dict(artifact),
            "outgoing": [dict(row) for row in outgoing],
            "incoming": [dict(row) for row in incoming],
        }

    def unverified_requirements(self) -> list[dict[str, str]]:
        if not self.db_path.exists():
            self.rebuild()
        with sqlite3.connect(self.db_path, timeout=15) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT a.id, a.title, a.status
                FROM artifacts a
                LEFT JOIN links l ON l.src_id = a.id AND l.link_type = 'verified_by'
                WHERE a.kind = 'requirement' AND a.status IN ('approved', 'implemented') AND l.dst_id IS NULL
                ORDER BY a.id
                """
            ).fetchall()
        return [dict(row) for row in rows]
