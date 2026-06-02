"""Tests for webhook system: registration, dispatch, signing, event filtering."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import specforge_daemon.api as _api
from specforge_core.config import ProjectConfig, load_config, save_config
from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_core.webhooks import WebhookEntry, fire_event
from specforge_daemon.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_daemon(monkeypatch):
    """Reset daemon globals for webhook tests."""
    if _api._watcher is not None:
        _api._watcher.stop()
        _api._watcher = None
    _api._active_project = None
    monkeypatch.setattr("specforge_daemon.watcher.ProjectWatcher.start", lambda self: None)
    yield
    if _api._watcher is not None:
        _api._watcher.stop()
        _api._watcher = None
    _api._active_project = None


class TestWebhookEntry:
    """Test WebhookEntry Pydantic model."""

    def test_webhook_entry_defaults(self) -> None:
        entry = WebhookEntry(url="https://example.com/hook")
        assert entry.url == "https://example.com/hook"
        assert entry.events == []
        assert entry.secret == ""

    def test_webhook_entry_with_events(self) -> None:
        entry = WebhookEntry(
            url="https://example.com/hook",
            events=["artifact.created", "artifact.promoted"],
        )
        assert entry.events == ["artifact.created", "artifact.promoted"]

    def test_webhook_entry_with_secret(self) -> None:
        entry = WebhookEntry(
            url="https://example.com/hook",
            secret="my-secret",
        )
        assert entry.secret == "my-secret"


class TestFireEvent:
    """Test fire_event dispatch and HMAC signing."""

    def test_fire_event_with_no_webhooks(self, tmp_path: Path) -> None:
        """fire_event returns immediately if no webhooks configured."""
        project = Project(tmp_path)
        project.init()
        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )
        # Should not raise or block
        fire_event(project, "artifact.created", artifact)

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_fire_event_posts_to_url(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """fire_event POSTs to registered URL."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(project.root)
        cfg.webhooks.append(
            WebhookEntry(url="https://example.com/hook", events=[])
        )
        save_config(project.root, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        # Create artifact fires webhook
        time.sleep(0.1)  # Let background thread run

        # Verify urlopen was called
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.full_url == "https://example.com/hook"
        assert request.data is not None

        # Verify payload structure
        payload = json.loads(request.data)
        assert payload["event"] == "artifact.created"
        assert payload["project"] == ""
        assert "timestamp" in payload
        assert payload["artifact"]["id"] == artifact.id
        assert payload["artifact"]["kind"] == "idea"
        assert payload["artifact"]["title"] == "Test"

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_fire_event_includes_hmac_header(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """fire_event adds X-SpecForge-Signature header when secret is set."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(project.root)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=[],
                secret="test-secret",
            )
        )
        save_config(project.root, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        time.sleep(0.1)

        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        # urllib normalizes header keys to lowercase
        sig_header = next(
            (v for k, v in request.headers.items() if k.lower() == "x-specforge-signature"),
            None,
        )
        assert sig_header is not None
        assert sig_header.startswith("sha256=")

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_fire_event_respects_event_filter(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """fire_event only fires if event is in webhook's events list."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(project.root)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=["artifact.promoted"],  # Only subscribe to promote events
            )
        )
        save_config(project.root, cfg)
        project.reload_config()

        # Create artifact fires "artifact.created" but webhook only subscribed to "artifact.promoted"
        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        time.sleep(0.1)

        # Should not have been called (event mismatch)
        assert not mock_urlopen.called

        # Now promote, which should fire
        promoted = project.promote_artifact(artifact.id, ArtifactKind.CANDIDATE)
        time.sleep(0.1)

        assert mock_urlopen.called

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_fire_event_swallows_exceptions(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """fire_event never raises or blocks, logs to stderr."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(project.root)
        cfg.webhooks.append(
            WebhookEntry(url="https://example.com/hook", events=[])
        )
        save_config(project.root, cfg)
        project.reload_config()

        # Mock urlopen to raise an exception
        mock_urlopen.side_effect = Exception("Network error")

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        # Should not raise
        time.sleep(0.1)
        # Test passes if we get here without exception


class TestWebhookCLI:
    """Test CLI webhook commands."""

    def test_webhook_add_via_cli(self, tmp_path: Path) -> None:
        """Test specforge webhook add command."""
        from typer.testing import CliRunner
        from specforge_cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "webhook",
                str(tmp_path),
                "add",
                "https://example.com/hook",
                "--event",
                "artifact.created",
                "--secret",
                "test-secret",
            ],
        )
        assert result.exit_code == 0
        assert "Added webhook" in result.stdout

        cfg = load_config(tmp_path)
        assert len(cfg.webhooks) == 1
        assert cfg.webhooks[0].url == "https://example.com/hook"
        assert cfg.webhooks[0].events == ["artifact.created"]
        assert cfg.webhooks[0].secret == "test-secret"

    def test_webhook_list_via_cli(self, tmp_path: Path) -> None:
        """Test specforge webhook list command."""
        from typer.testing import CliRunner
        from specforge_cli.main import app

        # Set up project with webhooks
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook1",
                events=["artifact.created"],
                secret="secret1",
            )
        )
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook2",
                events=[],
                secret="",
            )
        )
        save_config(tmp_path, cfg)

        runner = CliRunner()
        result = runner.invoke(app, ["webhook", str(tmp_path), "list"])
        assert result.exit_code == 0
        assert "https://example.com/hook1" in result.stdout
        assert "https://example.com/hook2" in result.stdout

    def test_webhook_remove_via_cli(self, tmp_path: Path) -> None:
        """Test specforge webhook remove command."""
        from typer.testing import CliRunner
        from specforge_cli.main import app

        # Set up project with webhooks
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(url="https://example.com/hook1", events=[])
        )
        cfg.webhooks.append(
            WebhookEntry(url="https://example.com/hook2", events=[])
        )
        save_config(tmp_path, cfg)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["webhook", str(tmp_path), "remove", "https://example.com/hook1"],
        )
        assert result.exit_code == 0
        assert "Removed webhook" in result.stdout

        cfg = load_config(tmp_path)
        assert len(cfg.webhooks) == 1
        assert cfg.webhooks[0].url == "https://example.com/hook2"

    @patch("urllib.request.urlopen")
    def test_webhook_test_via_cli(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Test specforge webhook test command."""
        from typer.testing import CliRunner
        from specforge_cli.main import app

        # Set up project with webhooks
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(url="https://example.com/hook", events=[])
        )
        save_config(tmp_path, cfg)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["webhook", str(tmp_path), "test", "https://example.com/hook"],
        )
        assert result.exit_code == 0
        assert "Ping sent" in result.stdout

        # Verify urlopen was called
        assert mock_urlopen.called
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data)
        assert payload["event"] == "webhook.ping"


class TestWebhookDaemon:
    """Test daemon webhook endpoints."""

    def test_daemon_list_webhooks(self, tmp_path: Path) -> None:
        """Test GET /webhooks endpoint."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook1",
                events=["artifact.created"],
                secret="secret",
            )
        )
        save_config(tmp_path, cfg)

        # Open project in daemon
        client.post("/projects/open", json={"path": str(tmp_path)})

        response = client.get("/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com/hook1"
        assert data[0]["events"] == ["artifact.created"]
        assert data[0]["secret"] is True

    def test_daemon_add_webhook(self, tmp_path: Path) -> None:
        """Test POST /webhooks endpoint."""
        project = Project(tmp_path)
        project.init()

        # Open project in daemon
        client.post("/projects/open", json={"path": str(tmp_path)})

        response = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["artifact.created"],
                "secret": "test-secret",
            },
        )
        assert response.status_code == 200
        assert "Webhook added" in response.json()["ok"]

        cfg = load_config(tmp_path)
        assert len(cfg.webhooks) == 1
        assert cfg.webhooks[0].url == "https://example.com/hook"

    def test_daemon_remove_webhook(self, tmp_path: Path) -> None:
        """Test DELETE /webhooks/{url} endpoint."""
        project = Project(tmp_path)
        project.init()

        # Open project in daemon first
        client.post("/projects/open", json={"path": str(tmp_path)})

        # Add a webhook via daemon
        client.post(
            "/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": [],
                "secret": "",
            },
        )

        from urllib.parse import quote

        response = client.delete(
            "/webhooks",
            params={"url": "https://example.com/hook"},
        )
        assert response.status_code == 200
        assert "Webhook removed" in response.json()["ok"]

        cfg = load_config(tmp_path)
        assert len(cfg.webhooks) == 0


class TestWebhookIntegration:
    """Test webhook integration with artifact lifecycle."""

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_webhook_fired_on_create_artifact(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Test that create_artifact fires webhook."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=["artifact.created"],
            )
        )
        save_config(tmp_path, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        time.sleep(0.1)
        assert mock_urlopen.called

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_webhook_fired_on_promote_artifact(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Test that promote_artifact fires webhook."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=["artifact.promoted"],
            )
        )
        save_config(tmp_path, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        time.sleep(0.1)
        mock_urlopen.reset_mock()

        promoted = project.promote_artifact(artifact.id, ArtifactKind.CANDIDATE)
        time.sleep(0.1)
        assert mock_urlopen.called

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_webhook_fired_on_update_status(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Test that update_status fires webhook."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=["artifact.status_changed"],
            )
        )
        save_config(tmp_path, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        time.sleep(0.1)
        mock_urlopen.reset_mock()

        project.update_status(artifact.id, ArtifactStatus.PROPOSED)
        time.sleep(0.1)
        assert mock_urlopen.called

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_webhook_fired_on_link_artifact(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Test that link_artifact fires webhook."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=["artifact.linked"],
            )
        )
        save_config(tmp_path, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
        )

        time.sleep(0.1)
        mock_urlopen.reset_mock()

        project.link_artifact(artifact.id, tags=["v1.0"])
        time.sleep(0.1)
        assert mock_urlopen.called

    @patch("specforge_core.webhooks.urllib.request.urlopen")
    def test_webhook_fired_on_unlink_artifact(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        """Test that unlink_artifact fires webhook."""
        project = Project(tmp_path)
        project.init()
        cfg = load_config(tmp_path)
        cfg.webhooks.append(
            WebhookEntry(
                url="https://example.com/hook",
                events=["artifact.unlinked"],
            )
        )
        save_config(tmp_path, cfg)
        project.reload_config()

        artifact = project.create_artifact(
            ArtifactKind.IDEA,
            "Test",
            "Test body",
            tags=["v1.0"],
        )

        time.sleep(0.1)
        mock_urlopen.reset_mock()

        project.unlink_artifact(artifact.id, tags=["v1.0"])
        time.sleep(0.1)
        assert mock_urlopen.called
