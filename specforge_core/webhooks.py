"""Webhook dispatcher for artifact events.

Fires HTTP POST requests to registered webhook URLs whenever an artifact is created,
promoted, linked, or its status changes. HMAC-SHA256 signing optional.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

from pydantic import BaseModel


class WebhookEntry(BaseModel):
    url: str
    events: list[str] = []  # Empty list = subscribe to all events
    secret: str = ""


def fire_event(project: object, event: str, artifact: object) -> None:
    """Dispatch a webhook event in a background thread. Never blocks or raises.

    Args:
        project: The Project instance (has config attribute)
        event: Event name (e.g. "artifact.created")
        artifact: The Artifact instance that triggered the event
    """
    # Import here to avoid circular imports
    from .project import Project
    from .models import Artifact

    assert isinstance(project, Project)
    assert isinstance(artifact, Artifact)

    webhooks = project.config.webhooks
    if not webhooks:
        return

    thread = threading.Thread(
        target=_dispatch_webhooks, args=(webhooks, event, project.config.project_name, artifact),
        daemon=True,
    )
    thread.start()


def _dispatch_webhooks(
    webhooks: list[WebhookEntry], event: str, project_name: str, artifact: object
) -> None:
    """Fire all matching webhooks. Logs errors to stderr, never raises."""
    for entry in webhooks:
        # Skip if webhook doesn't subscribe to this event
        if entry.events and event not in entry.events:
            continue
        _fire_webhook(entry, event, project_name, artifact)


def _fire_webhook(entry: WebhookEntry, event: str, project_name: str, artifact: object) -> None:
    """Fire a single webhook. Never raises."""
    try:
        from .models import Artifact
        assert isinstance(artifact, Artifact)

        payload = {
            "event": event,
            "project": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifact": {
                "id": artifact.id,
                "kind": artifact.kind.value,
                "status": artifact.status.value,
                "title": artifact.title,
                "source": artifact.source,
                "tags": artifact.tags,
            },
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        if entry.secret:
            sig = hmac.new(
                entry.secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()
            headers["X-SpecForge-Signature"] = f"sha256={sig}"

        request = urllib.request.Request(
            entry.url, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
    except Exception as exc:
        import sys
        print(f"Webhook {entry.url} failed: {exc}", file=sys.stderr)
