# Webhooks

Webhooks let external tools react to SpecForge artifact events in real
time — without polling. When an artifact is created, promoted, linked,
or its status changes, SpecForge POSTs a JSON payload to every
registered URL.

Common uses: Slack notifications, GitHub Actions triggers, CI
pipelines, custom dashboards, Jira syncing.

---

## Adding a webhook

```bash
specforge webhook ./proj add https://hooks.slack.com/services/XXX \
  --event artifact.created \
  --event artifact.promoted \
  --secret "optional-signing-secret"
```

Omit `--event` to subscribe to **all** events:

```bash
specforge webhook ./proj add https://ci.example.com/specforge
```

---

## Managing webhooks

```bash
# List all registered webhooks
specforge webhook ./proj list

# Test connectivity (fires a synthetic webhook.ping event)
specforge webhook ./proj test https://hooks.slack.com/services/XXX

# Remove a webhook
specforge webhook ./proj remove https://hooks.slack.com/services/XXX
```

---

## Events

| Event | Fired when |
|-------|-----------|
| `artifact.created` | `specforge add-*` or `specforge draft` creates an artifact |
| `artifact.promoted` | `specforge promote` creates a promoted artifact |
| `artifact.status_changed` | `specforge update-status` changes an artifact's status |
| `artifact.linked` | `specforge link` adds links to an artifact |
| `artifact.unlinked` | `specforge unlink` removes links from an artifact |

---

## Payload structure

Every POST body is JSON:

```json
{
  "event": "artifact.created",
  "project": "My Project",
  "timestamp": "2026-06-01T14:23:01.123456+00:00",
  "artifact": {
    "id":     "REQ-0001",
    "kind":   "requirement",
    "status": "approved",
    "title":  "Export DXF files",
    "source": "CAND-0001",
    "tags":   ["v1.0", "export"]
  }
}
```

The `webhook.ping` event (sent by `specforge webhook test`) has
`"artifact": null`.

---

## HMAC-SHA256 signing

If you provide a `--secret`, SpecForge adds a signature header to
every request so your receiver can verify the payload is genuine.

**Header:**
```
X-SpecForge-Signature: sha256=<hex-digest>
```

**How to verify in Python:**

```python
import hashlib, hmac

def verify(body: bytes, secret: str, header: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)
```

**How to verify in Node.js:**

```javascript
const crypto = require('crypto');

function verify(body, secret, header) {
  const expected = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(body)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(expected), Buffer.from(header)
  );
}
```

---

## Delivery behaviour

- Webhooks fire **after** the artifact is written to disk.
- Delivery runs in a **background thread** — it never blocks the CLI
  or daemon response.
- **Single attempt, 5-second timeout.** There is no automatic retry.
- Failures are logged to `stderr` but do not affect the artifact
  operation.

---

## Config file format

Webhooks can also be managed directly in `.specforge.yaml`:

```yaml
webhooks:
  - url: https://hooks.slack.com/services/XXX/YYY/ZZZ
    events: [artifact.created, artifact.promoted]
    secret: "my-signing-secret"

  - url: https://ci.example.com/specforge
    events: []           # subscribe to all events
    secret: ""
```

---

## Daemon REST endpoints

When the daemon is running, webhooks can also be managed over HTTP:

```
GET    /webhooks               List registered webhooks
POST   /webhooks               Add a webhook {url, events, secret}
DELETE /webhooks?url=<url>     Remove a webhook by URL
```
