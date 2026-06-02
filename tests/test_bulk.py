"""Tests for bulk artifact operations."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.bulk import bulk_update
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project

runner = CliRunner()


def _setup_project(tmp_path: Path) -> tuple[Project, list]:
    p = Project(tmp_path)
    p.init()
    a1 = p.create_artifact(ArtifactKind.TASK, "Task 1", "body", tags=["v1"])
    a2 = p.create_artifact(ArtifactKind.TASK, "Task 2", "body", tags=["v2"])
    a3 = p.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", "body", tags=["v1"])
    return p, [a1, a2, a3]


class TestBulkFilter:
    def test_filter_by_kind(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        matched = bulk_update(p, "archive", {"kind": ["task"]}, {}, dry_run=True)
        assert all(a.kind == ArtifactKind.TASK for a in matched)
        assert len(matched) == 2

    def test_filter_by_status(self, tmp_path: Path) -> None:
        p, arts = _setup_project(tmp_path)
        p.update_status(arts[0].id, ArtifactStatus.IMPLEMENTED)
        matched = bulk_update(p, "archive", {"status": "implemented"}, {}, dry_run=True)
        assert len(matched) == 1
        assert matched[0].id == arts[0].id

    def test_filter_by_tag(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        matched = bulk_update(p, "archive", {"tag": ["v1"]}, {}, dry_run=True)
        assert len(matched) == 2

    def test_filter_combined(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        matched = bulk_update(p, "archive", {"kind": ["task"], "tag": ["v1"]}, {}, dry_run=True)
        assert len(matched) == 1
        assert matched[0].kind == ArtifactKind.TASK

    def test_no_match_returns_empty(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        matched = bulk_update(p, "archive", {"tag": ["nonexistent"]}, {}, dry_run=True)
        assert matched == []


class TestBulkActions:
    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        p, arts = _setup_project(tmp_path)
        bulk_update(p, "update-status", {"kind": ["task"]}, {"to_status": "implemented"}, dry_run=True)
        # Re-load — statuses should be unchanged
        for a in arts[:2]:
            fresh = p.get_artifact(a.id)
            assert fresh.status == ArtifactStatus.DRAFT

    def test_update_status_changes_matching_artifacts(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        affected = bulk_update(p, "update-status", {"kind": ["task"]}, {"to_status": "implemented"})
        assert len(affected) == 2
        for a in affected:
            fresh = p.get_artifact(a.id)
            assert fresh.status == ArtifactStatus.IMPLEMENTED

    def test_archive_sets_archived_status(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        affected = bulk_update(p, "archive", {"kind": ["task"]}, {})
        for a in affected:
            fresh = p.get_artifact(a.id)
            assert fresh.status == ArtifactStatus.ARCHIVED

    def test_tag_add_appends_tags(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        bulk_update(p, "tag-add", {"kind": ["requirement"]}, {"tags": ["sprint-1"]})
        req = next(a for a in p.artifacts() if a.kind == ArtifactKind.REQUIREMENT)
        assert "sprint-1" in req.tags

    def test_tag_remove_removes_tags(self, tmp_path: Path) -> None:
        p, arts = _setup_project(tmp_path)
        bulk_update(p, "tag-remove", {"kind": ["task"], "tag": ["v1"]}, {"tags": ["v1"]})
        # Only the v1-tagged task should be modified
        fresh = p.get_artifact(arts[0].id)
        assert "v1" not in fresh.tags

    def test_unknown_action_raises(self, tmp_path: Path) -> None:
        p, _ = _setup_project(tmp_path)
        with pytest.raises(ValueError, match="Unknown bulk action"):
            bulk_update(p, "fly", {}, {})


class TestBulkCLI:
    def test_bulk_dry_run(self, tmp_path: Path) -> None:
        p = Project(tmp_path)
        p.init()
        p.create_artifact(ArtifactKind.TASK, "Task 1", "body")
        result = runner.invoke(
            app,
            ["bulk", str(tmp_path), "update-status", "--kind", "task",
             "--to", "implemented", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output or "Dry run" in result.output
        # Status should still be draft
        fresh = p.artifacts()[0]
        assert fresh.status == ArtifactStatus.DRAFT

    def test_bulk_update_status(self, tmp_path: Path) -> None:
        p = Project(tmp_path)
        p.init()
        p.create_artifact(ArtifactKind.TASK, "Task 1", "body")
        p.create_artifact(ArtifactKind.TASK, "Task 2", "body")
        result = runner.invoke(
            app,
            ["bulk", str(tmp_path), "update-status",
             "--kind", "task", "--to", "implemented"],
        )
        assert result.exit_code == 0
        for a in p.artifacts():
            if a.kind == ArtifactKind.TASK:
                assert a.status == ArtifactStatus.IMPLEMENTED

    def test_bulk_no_match_prints_message(self, tmp_path: Path) -> None:
        p = Project(tmp_path)
        p.init()
        result = runner.invoke(
            app,
            ["bulk", str(tmp_path), "archive", "--kind", "task"],
        )
        assert result.exit_code == 0
        assert "No artifacts" in result.output

    def test_bulk_invalid_action_exits_1(self, tmp_path: Path) -> None:
        p = Project(tmp_path)
        p.init()
        p.create_artifact(ArtifactKind.TASK, "Task 1", "body")
        result = runner.invoke(app, ["bulk", str(tmp_path), "fly"])
        assert result.exit_code == 1
