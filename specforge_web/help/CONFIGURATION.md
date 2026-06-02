# Configuration Reference

Each SpecForge project has an optional `.specforge.yaml` file at its
root. All settings are optional — omit any key to use the default.

---

## Full example

```yaml
# Human-readable project name (used in reports and the status dashboard)
project_name: "My Project"

# Auto-commit every artifact write to git
# Equivalent to passing --git on every command
git_commit: false

# LLM provider for 'specforge draft'
llm:
  provider: anthropic          # anthropic | openai | ollama
  model: claude-sonnet-4-6     # blank = use provider default
  api_key: ""                  # blank = read from env var
  base_url: ""                 # blank = use provider default

# Webhooks — POST to these URLs on artifact events
webhooks:
  - url: https://hooks.slack.com/services/XXX/YYY/ZZZ
    events: [artifact.created, artifact.promoted]
    secret: "optional-hmac-secret"
  - url: https://ci.example.com/specforge
    events: []                 # empty = subscribe to all events
```

---

## Settings reference

### `project_name`

Type: string — Default: `""`

Used in acceptance report titles and the status dashboard heading.

```bash
specforge init ./proj --name "Drawing Export System"
# or later:
specforge config ./proj --set project_name="Drawing Export System"
```

---

### `git_commit`

Type: boolean — Default: `false`

When `true`, every artifact write is committed to git automatically,
as if you had passed `--git` on every command. The `--git` flag on
individual commands always overrides this setting.

```bash
specforge config ./proj --set git_commit=true
```

---

### `llm`

Settings for the AI drafting provider. See **AI Drafting** in the
Help menu for full setup instructions.

| Key | Default | Description |
|-----|---------|-------------|
| `provider` | `anthropic` | `anthropic`, `openai`, or `ollama` |
| `model` | *(provider default)* | Model name. Defaults: `claude-sonnet-4-6`, `gpt-4o-mini`, `llama3.2` |
| `api_key` | `""` | API key. Falls back to `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` env vars |
| `base_url` | `""` | Override the provider endpoint. Useful for Ollama or OpenAI-compatible servers |

```bash
# Set provider
specforge config ./proj --set llm.provider=ollama

# Set model
specforge config ./proj --set llm.model=llama3.2

# Set Ollama endpoint
specforge config ./proj --set llm.base_url=http://localhost:11434
```

---

### `webhooks`

A list of webhook entries. Each entry can subscribe to specific events
or all events (empty `events` list).

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | The endpoint to POST to |
| `events` | list | Event names to subscribe to. Empty = all events |
| `secret` | string | Optional HMAC-SHA256 signing secret |

**Webhook events:**

| Event | Fired when |
|-------|-----------|
| `artifact.created` | A new artifact is created |
| `artifact.promoted` | An artifact is promoted to a new kind |
| `artifact.status_changed` | An artifact's status is updated |
| `artifact.linked` | Links are added to an artifact |
| `artifact.unlinked` | Links are removed from an artifact |

**HMAC verification** — if `secret` is set, SpecForge adds an
`X-SpecForge-Signature: sha256=<hex>` header to every POST. Verify
it on your receiver to confirm the payload came from SpecForge.

Manage webhooks via CLI:

```bash
specforge webhook ./proj add https://example.com/hook \
  --event artifact.created \
  --event artifact.promoted \
  --secret "my-secret"

specforge webhook ./proj list
specforge webhook ./proj test https://example.com/hook
specforge webhook ./proj remove https://example.com/hook
```

---

## Managing config via CLI

```bash
# Show current config
specforge config ./proj

# Set a top-level key
specforge config ./proj --set git_commit=true
specforge config ./proj --set project_name="New Name"

# Set a nested LLM key (dotted syntax)
specforge config ./proj --set llm.provider=ollama
specforge config ./proj --set llm.model=mistral
specforge config ./proj --set llm.api_key=sk-...
```

---

## Location and format

The file is always `.specforge.yaml` at the project root. It is
created with a commented template when you run `specforge init`.

The file is plain YAML and is safe to commit to git, **unless** you
store API keys in `llm.api_key` — in that case, add `.specforge.yaml`
to `.gitignore` and use environment variables instead.
