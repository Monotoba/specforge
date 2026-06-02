# Plugin System

Plugins let you run custom Python code whenever an artifact changes —
auto-tagging rules, Slack notifications, validation side-effects, audit
logging, or anything else you can code. Unlike webhooks, plugins run
**locally in the same process**, synchronously, and have full access to
the `Project` object.

---

## How plugins work

1. Drop a `.py` file into `.specforge/plugins/`
2. Define an `on_event(event, artifact, project)` function
3. That's it — the plugin is active immediately

No configuration, no registration, no restart required.

---

## Creating a plugin

```bash
# Open the example plugin in your editor
specforge template ./proj edit task   # (just as an example of $EDITOR)

# Or create directly
cat > ./.proj/.specforge/plugins/my_hook.py << 'EOF'
def on_event(event, artifact, project):
    if event == "artifact.created" and artifact.kind.value == "task":
        print(f"[hook] New task: {artifact.id} — {artifact.title}")
EOF
```

Or open the pre-installed example:

```
.specforge/plugins/example_plugin.py.disabled
```

Rename it (remove `.disabled`) and edit it to activate.

---

## The `on_event` function

```python
def on_event(event: str, artifact, project) -> None:
    """
    Called synchronously after every artifact mutation.

    event    - one of the event names below
    artifact - specforge_core.models.Artifact instance
    project  - specforge_core.project.Project instance
    """
```

### Event names

| Event | Triggered by |
|-------|-------------|
| `artifact.created` | `create_artifact()` / `specforge add-*` / `specforge draft` |
| `artifact.promoted` | `promote_artifact()` / `specforge promote` |
| `artifact.status_changed` | `update_status()` / `specforge update-status` |
| `artifact.linked` | `link_artifact()` / `specforge link` |
| `artifact.unlinked` | `unlink_artifact()` / `specforge unlink` |

### Available artifact fields

```python
artifact.id           # "REQ-0001"
artifact.kind         # ArtifactKind enum  (.value gives "requirement")
artifact.status       # ArtifactStatus enum (.value gives "approved")
artifact.title        # "Export DXF files"
artifact.body         # Markdown body text
artifact.tags         # ["v1.0", "export"]
artifact.source       # "CAND-0001" or None
artifact.implements   # ["REQ-0001"]
artifact.depends_on   # ["TASK-0002"]
```

### Available project methods

```python
project.root          # pathlib.Path to the project directory
project.config        # ProjectConfig (project_name, git_commit, llm, webhooks)
project.artifacts()   # list of all Artifact objects (cached)
project.get_artifact(id)  # look up a single artifact by ID
```

---

## Error handling

Plugin exceptions are **caught and printed to stderr**. The artifact
mutation always completes — a buggy plugin cannot break your workflow.

```
Plugin /path/to/my_hook.py error: division by zero
```

Fix the plugin and the next mutation will run it cleanly.

---

## Listing plugins

```bash
specforge plugin ./proj list
```

Output shows each `.py` file in `.specforge/plugins/` and whether it
defines `on_event`:

```
         Plugins (/path/to/.specforge/plugins)
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ File                    ┃ on_event ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ audit_log.py            │ yes      │
│ slack_notify.py         │ yes      │
│ broken.py               │ error: … │
└─────────────────────────┴──────────┘
```

---

## Example plugins

### Audit log

```python
# .specforge/plugins/audit_log.py
from datetime import datetime, timezone
from pathlib import Path

def on_event(event, artifact, project):
    log = project.root / ".specforge" / "audit.log"
    ts = datetime.now(timezone.utc).isoformat()
    with open(log, "a") as f:
        f.write(f"{ts}  {event}  {artifact.id}  {artifact.title}\n")
```

### Auto-tag by kind

```python
# .specforge/plugins/auto_tag.py
def on_event(event, artifact, project):
    if event != "artifact.created":
        return
    if artifact.kind.value == "task" and "sprint-current" not in artifact.tags:
        project.link_artifact(artifact.id, tags=["sprint-current"])
```

### Slack notification

```python
# .specforge/plugins/slack_notify.py
import json, urllib.request

SLACK_URL = "https://hooks.slack.com/services/XXX/YYY/ZZZ"

def on_event(event, artifact, project):
    if event not in ("artifact.created", "artifact.status_changed"):
        return
    text = f"*{event}* — `{artifact.id}` {artifact.title} [{artifact.status.value}]"
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(SLACK_URL, data=body,
                                  headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        print(f"[slack] send failed: {e}")
```

---

## Plugin caching

Plugins are loaded once per `Project` instance (i.e. once per CLI
invocation or daemon request). If you edit a plugin file, the next
command will pick up the changes automatically.
