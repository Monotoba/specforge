from __future__ import annotations

import sqlite3

from .models import ArtifactKind, ArtifactStatus
from .project import Project
from .trace import TraceIndex


def search_artifacts(
    project: Project,
    query: str,
    kinds: list[ArtifactKind] | None = None,
    statuses: list[ArtifactStatus] | None = None,
    tags: list[str] | None = None,
) -> list[dict[str, object]]:
    """Search artifacts by keyword. All terms must match (title OR body per term).

    Returns a list of result dicts with id, kind, status, title, snippet, path.
    """
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return []

    index = TraceIndex(project)
    if not index.db_path.exists():
        index.rebuild()

    with sqlite3.connect(index.db_path, timeout=15) as conn:
        conn.row_factory = sqlite3.Row

        # Build WHERE clause: each term must appear in title OR body
        conditions: list[str] = []
        params: list[str] = []
        for term in terms:
            pattern = f"%{term}%"
            conditions.append("(a.title LIKE ? OR COALESCE(b.body, '') LIKE ?)")
            params.extend([pattern, pattern])

        if kinds:
            placeholders = ",".join("?" * len(kinds))
            conditions.append(f"a.kind IN ({placeholders})")
            params.extend(k.value for k in kinds)

        if statuses:
            placeholders = ",".join("?" * len(statuses))
            conditions.append(f"a.status IN ({placeholders})")
            params.extend(s.value for s in statuses)

        if tags:
            for tag in tags:
                conditions.append(
                    "EXISTS (SELECT 1 FROM tags t WHERE t.artifact_id = a.id AND t.tag = ?)"
                )
                params.append(tag)

        where = " AND ".join(conditions)
        sql = f"""
            SELECT a.id, a.kind, a.status, a.title, a.path, COALESCE(b.body, '') AS body
            FROM artifacts a
            LEFT JOIN bodies b ON b.id = a.id
            WHERE {where}
            ORDER BY a.kind, a.id
        """
        rows = conn.execute(sql, params).fetchall()

    results: list[dict[str, object]] = []
    for row in rows:
        results.append({
            "id": row["id"],
            "kind": row["kind"],
            "status": row["status"],
            "title": row["title"],
            "path": row["path"],
            "snippet": _snippet(row["body"], terms),
        })
    return results


def _snippet(body: str, terms: list[str]) -> str:
    """Return the first line of body that contains any search term, truncated to 120 chars."""
    lower_terms = [t.lower() for t in terms]
    for line in body.splitlines():
        if any(t in line.lower() for t in lower_terms):
            line = line.strip()
            return line[:120] + ("…" if len(line) > 120 else "")
    # No matching line found; return start of body
    first = body.strip()[:120]
    return first + ("…" if len(body.strip()) > 120 else "")
