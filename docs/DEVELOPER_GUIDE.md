# Developer Guide

This guide covers extending SpecForge: writing plugins, creating
webhooks, using the REST API, integrating with MCP, and contributing
to the codebase.

---

## Development setup

```bash
git clone <repo> specforge
cd specforge
pip install -e ".[dev,desktop]" --break-system-packages

# Run all tests
pytest

# Enable auto-reload during daemon development
SPECFORGE_DEV=1 specforge-daemon

# Start desktop app (requires desktop extras)
specforge-studio
```

---

## Writing plugins

Plugins are the simplest extension mechanism. Drop a `.py` file into
`.specforge/plugins/` and define `on_event`:

```python
def on_event(event: str, artifact, project) -> None:
    pass
```

### Event types

| Event | When |
|-------|------|
| `artifact.created` | New artifact written to disk |
| `artifact.promoted` | Artifact promoted to new kind |
| `artifact.status_changed` | Status updated |
| `artifact.linked` | Links added |
| `artifact.unlinked` | Links removed |

### Available objects

**`artifact`** — `specforge_core.models.Artifact` instance:

```python
artifact.id          # "REQ-0001"
artifact.kind        # ArtifactKind enum (.value = "requirement")
artifact.status      # ArtifactStatus enum (.value = "approved")
artifact.title       # "Export DXF files"
artifact.body        # Markdown string
artifact.tags        # ["v1.0", "export"]
artifact.source      # "CAND-0001" or None
artifact.implements  # ["REQ-0001"]
```

**`project`** — `specforge_core.project.Project` instance:

```python
project.root              # pathlib.Path to project directory
project.config            # ProjectConfig
project.artifacts()       # list[Artifact], cached
project.get_artifact(id)  # look up by ID
```

### Error handling

Exceptions in `on_event` are caught and printed to stderr. The
artifact mutation always completes. Use try/except internally for any
external I/O in plugins.

### Example: auto-tag by kind

```python
# .specforge/plugins/sprint_tagger.py
CURRENT_SPRINT = "sprint-13"

def on_event(event, artifact, project):
    if event != "artifact.created":
        return
    if artifact.kind.value == "task" and CURRENT_SPRINT not in artifact.tags:
        project.link_artifact(artifact.id, tags=[CURRENT_SPRINT])
```

### Example: Slack notification

```python
# .specforge/plugins/slack_notify.py
import json, urllib.request

WEBHOOK_URL = "https://hooks.slack.com/services/XXX/YYY/ZZZ"
NOTIFY_EVENTS = {"artifact.created", "artifact.status_changed"}

def on_event(event, artifact, project):
    if event not in NOTIFY_EVENTS:
        return
    text = (
        f"*{project.config.project_name}* — "
        f"`{artifact.id}` ({artifact.kind.value}) "
        f"*{event.split('.')[1]}*: {artifact.title} "
        f"[{artifact.status.value}]"
    )
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        WEBHOOK_URL, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception as exc:
        import sys
        print(f"[slack] {exc}", file=sys.stderr)
```

---

## Webhooks

Webhooks are configured in `.specforge.yaml` and fire for all users
of the project. The payload format is fixed JSON.

```yaml
webhooks:
  - url: https://ci.example.com/specforge
    events: [artifact.created, artifact.promoted]
    secret: "shared-hmac-secret"
```

### Payload

```json
{
  "event": "artifact.created",
  "project": "My Project",
  "timestamp": "2026-06-02T10:00:00+00:00",
  "artifact": {
    "id": "REQ-0001",
    "kind": "requirement",
    "status": "approved",
    "title": "Export DXF files",
    "source": "CAND-0001",
    "tags": ["v1.0"]
  }
}
```

### HMAC verification (Python receiver)

```python
import hashlib, hmac
from fastapi import Request, HTTPException

async def verify_specforge_webhook(request: Request, secret: str):
    body = await request.body()
    sig_header = request.headers.get("x-specforge-signature", "")
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=403, detail="Invalid signature")
    return body
```

---

## REST API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/ui` | Web UI HTML |
| `POST` | `/projects/open` | Open a project |
| `GET` | `/artifacts` | List (`?kind=&status=&tag=`) |
| `POST` | `/artifacts` | Create artifact |
| `GET` | `/artifacts/{id}` | Get artifact |
| `POST` | `/artifacts/{id}/promote` | Promote |
| `PATCH` | `/artifacts/{id}/status` | Update status |
| `POST` | `/artifacts/{id}/link` | Add links |
| `POST` | `/artifacts/{id}/unlink` | Remove links |
| `POST` | `/trace/rebuild` | Rebuild index |
| `GET` | `/trace/{id}` | Artifact graph |
| `GET` | `/search?q=` | Full-text search |
| `GET` | `/context-pack` | AI context pack |
| `GET` | `/report` | Acceptance report |
| `GET` | `/status` | Project dashboard |
| `GET` | `/validate` | Validation check |
| `GET` | `/export` | Traceability matrix |
| `GET` | `/git/log` | Git history |
| `POST` | `/tool-call` | AI adapter dispatch |
| `GET` | `/webhooks` | List webhooks |
| `POST` | `/webhooks` | Add webhook |
| `DELETE` | `/webhooks?url=` | Remove webhook |
| `GET` | `/help` | List help topics |
| `GET` | `/help/{topic}` | Get help markdown |

---

## MCP tool development

To add a new MCP tool, update `specforge_daemon/mcp_server.py`:

```python
TOOLS = [
    # existing tools...
    {
        "name": "my_new_tool",
        "description": "What this tool does.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "..."}
            },
            "required": ["param"]
        }
    }
]
```

Add a handler in the dispatch section of `handle_call`:

```python
elif name == "my_new_tool":
    result = some_core_function(project, call["param"])
    return {"ok": True, "result": result}
```

---

## Adding a new artifact kind

1. Add to `ArtifactKind` in `models.py`
2. Add prefix to `_KIND_PREFIXES` in `idgen.py`
3. Add directory mapping to `DIR_BY_KIND` and `ROOT_DIRS` in `project.py`
4. Add CLI command in `specforge_cli/main.py`
5. Add badge CSS in `specforge_web/index.html`
6. Update `_KINDS` in `specforge_studio/main.py`
7. Write tests

---

## Test patterns

```python
# Core tests — use tmp_path, no mocking
def test_create_artifact(tmp_path):
    project = Project(tmp_path)
    project.init()
    artifact = project.create_artifact(
        ArtifactKind.IDEA, "Test", "Body"
    )
    assert artifact.id.startswith("IDEA-")

# CLI tests — use CliRunner
from typer.testing import CliRunner
def test_cli(tmp_path):
    result = CliRunner().invoke(app, ["add-idea", str(tmp_path), "Title"])
    assert result.exit_code == 0

# Daemon tests — use TestClient
from fastapi.testclient import TestClient
def test_api(tmp_path):
    client = TestClient(app)
    client.post("/projects/open", json={"path": str(tmp_path)})
    r = client.post("/artifacts", json={"kind": "idea", "title": "T", "body": "B"})
    assert r.status_code == 200

# LLM tests — mock urlopen
@patch("specforge_core.llm.urllib.request.urlopen")
def test_llm(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"content": [{"text": "result"}]}
    ).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp
    result = complete("prompt", "system", LLMConfig(api_key="sk-x"))
    assert result == "result"
```

---

## Commit guidelines

- Small, focused commits
- Every feature includes tests
- Update relevant documentation
- Add CHANGELOG.md entry
- `specforge_core` must remain free of HTTP and UI dependencies

```bash
pytest && ruff check specforge_core specforge_cli specforge_daemon
git add <specific files>
git commit -m "Descriptive message"
```
