# AI Drafting

The `specforge draft` command generates artifact body content using a
large language model. You describe what you want in plain English and
SpecForge writes the Markdown for you.

---

## Quick start

```bash
specforge draft ./proj requirement \
  "The API must accept requests only over HTTPS with TLS 1.2 or later" \
  --title "TLS requirement"
```

SpecForge calls your LLM, displays the generated body in a panel, and
asks: **Create artifact? [Y/n]**. Press Enter to accept or `n` to
discard.

---

## Supported providers

| Provider | Default model | Config key |
|----------|--------------|------------|
| Anthropic | `claude-sonnet-4-6` | `anthropic` |
| OpenAI (and compatible) | `gpt-4o-mini` | `openai` |
| Ollama (local) | `llama3.2` | `ollama` |

All providers are called via standard HTTP — no additional Python
packages are required.

---

## Configuration

Set the provider once in your project config:

```bash
specforge config ./proj --set llm.provider=anthropic
specforge config ./proj --set llm.model=claude-opus-4-7
```

Or edit `.specforge.yaml` directly:

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-6
  api_key: ""        # leave blank to use env var
  base_url: ""       # leave blank for default endpoint
```

### API keys

**Anthropic** — set `ANTHROPIC_API_KEY` in your environment:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**OpenAI** — set `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY="sk-..."
```

**Ollama** — no API key needed. Ollama must be running locally.

Keys stored in `api_key:` in `.specforge.yaml` take precedence over
environment variables. Be careful not to commit secret keys to git —
the env var approach is safer.

---

## Using Ollama (local, no internet required)

Ollama runs models on your own machine. No API key, no cloud, no
cost per request — ideal if you work offline or have privacy concerns.

**Install Ollama** from [ollama.com](https://ollama.com), then pull a model:

```bash
ollama pull llama3.2       # ~2 GB, good general model
ollama pull mistral        # alternative
```

Configure SpecForge to use it:

```bash
specforge config ./proj --set llm.provider=ollama
```

The default Ollama endpoint is `http://localhost:11434`. Override if
you run Ollama on a different host:

```bash
specforge config ./proj --set llm.base_url=http://192.168.1.10:11434
```

---

## OpenAI-compatible servers

Any server that implements the OpenAI `/v1/chat/completions` API works
with the `openai` provider. Examples: LM Studio, vLLM, Jan, Groq.

```bash
specforge config ./proj --set llm.provider=openai
specforge config ./proj --set llm.base_url=http://localhost:1234
specforge config ./proj --set llm.model=lmstudio-community/Meta-Llama-3-8B
```

---

## Ollama fallback

When a remote provider (Anthropic or OpenAI) fails — network down,
API key expired, rate limited — SpecForge prompts:

```
LLM error: HTTP 401 …
Use local Ollama instead? [y/N]:
```

Press `y` to retry with Ollama. Press `n` to cancel. This lets you
keep working offline without changing your config.

---

## Command options

```
specforge draft <path> <kind> <prompt>
  --title TEXT       Override the artifact title (default: first 60 chars of prompt)
  --no-confirm       Create without asking for confirmation
  --tag TAG          Add one or more tags (repeatable)
  --git              Commit the created artifact to git
```

**Examples:**

```bash
# Draft a task with a specific title and tag
specforge draft ./proj task \
  "Implement presigned S3 URL upload flow for profile photos up to 5 MB" \
  --title "Photo upload — S3 presigned URL" \
  --tag sprint-12 --tag profile

# Draft and create immediately without confirmation
specforge draft ./proj idea \
  "Dark mode reduces eye strain for users with migraines" \
  --no-confirm --git
```

---

## Tips for good prompts

- **Be specific**: include the constraint, the context, and the
  acceptance criteria in the prompt.
- **Name the kind**: the system prompt already tells the LLM the
  artifact kind, but mentioning it in your prompt reinforces the format.
- **Iterate**: if the first draft isn't right, decline it and re-run
  with a more detailed prompt. The generated body is a starting point —
  use `specforge edit ./proj <id>` to refine after creation.
