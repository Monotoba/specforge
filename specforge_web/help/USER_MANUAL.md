# SpecForge User Manual

## Artifact kinds

| Kind | Purpose | Default status |
|------|---------|---------------|
| `idea` | Raw exploration note | draft |
| `candidate` | Idea promoted for evaluation | proposed |
| `requirement` | Approved, traceable requirement | approved |
| `decision` | Architectural or design decision | approved |
| `assumption` | Stated assumption that may need validation | draft |
| `constraint` | Non-negotiable constraint | draft |
| `change_order` | Proposed scope or requirement change | proposed |
| `task` | Development work item | draft |
| `test` | Test specification | draft |
| `verification` | Evidence that a requirement is met | draft |
| `reference` | External reference or source link | draft |
| `conversation` | Recorded conversation or meeting notes | draft |

## Status lifecycle

`draft → proposed → approved → implemented → verified`

Side transitions: `→ rejected`, `→ archived`

## CLI commands

### Project management

```
specforge init <path> [--git] [--name NAME]
```
Create a new project. `--git` initialises a git repository and commits the
scaffold. `--name` sets the project name used in reports.

```
specforge config <path> [--set key=value]
```
Show or update project configuration. Supports dotted keys for nested
settings (e.g. `--set llm.provider=ollama`).

### Adding artifacts

```
specforge add-idea <path> <title> [body] [--tag TAG] [--git]
specforge add-req  <path> <title> --text TEXT [--source ID] [--tag TAG] [--git]
specforge add-task <path> <title> --text TEXT [--implements ID] [--depends-on ID] [--git]
specforge add-test <path> <title> --text TEXT [--req ID] [--git]
specforge add-verification <path> <title> --text TEXT [--req ID] [--test ID] [--git]
specforge add-decision   <path> <title> --text TEXT [--req ID] [--git]
specforge add-assumption <path> <title> --text TEXT [--req ID]
specforge add-constraint <path> <title> --text TEXT [--req ID]
specforge add-co         <path> <title> --text TEXT [--git]
specforge add-ref        <path> <title> --text TEXT
specforge add-conv       <path> <title> --text TEXT
```

### AI drafting

```
specforge draft <path> <kind> <prompt> [--title TEXT] [--no-confirm] [--tag TAG] [--git]
```
Generate artifact body with an LLM. Displays the result and prompts for
confirmation. Supports Anthropic, OpenAI-compatible, and Ollama providers.

### Viewing and searching

```
specforge list   <path> [--kind KIND] [--status STATUS] [--tag TAG]
specforge show   <path> <id>
specforge search <path> <query> [--kind KIND] [--status STATUS] [--tag TAG]
specforge graph  <path> <id>
specforge status <path>
```

### Workflow

```
specforge promote       <path> <id> <target-kind> [--text TEXT] [--git]
specforge update-status <path> <id> <new-status>  [--git]
specforge link          <path> <id> [--implements ID] [--req ID] [--test ID]
                                    [--depends-on ID] [--source ID] [--tag TAG]
specforge unlink        <path> <id> [--implements ID] [--req ID] [--tag TAG] [--source]
specforge edit          <path> <id>        # opens in $EDITOR
```

### Bulk operations

```
specforge bulk <path> <action> [--kind KIND] [--status STATUS] [--tag TAG]
                               [--to STATUS] [--add-tag TAG] [--remove-tag TAG]
                               [--dry-run]
```
Actions: `update-status`, `archive`, `tag-add`, `tag-remove`

### Templates

```
specforge template <path> list
specforge template <path> new  <kind> [--title TEXT] [--no-confirm] [--tag TAG]
specforge template <path> edit <kind>   # opens in $EDITOR
```
Templates live in `.specforge/templates/<kind>.md`. Optional YAML front
matter (`tags:`, `status:`) is merged into the created artifact.

### Reports and export

```
specforge check        <path>                    # CI release gate
specforge report       <path> [--output FILE]    # acceptance report
specforge export       <path> [--format csv|markdown|both]
specforge context-pack <path> [--output FILE]    # AI context pack
specforge trace        <path>                    # rebuild SQLite trace index
specforge validate     <path>                    # validate links and status
specforge log          <path> [--n N]            # git artifact history
```

### Plugins and webhooks

```
specforge plugin  <path> list
specforge webhook <path> add    <url> [--event EVENT] [--secret SECRET]
specforge webhook <path> list
specforge webhook <path> remove <url>
specforge webhook <path> test   <url>
```

### MCP integration (Claude Code)

```
specforge mcp        <path>   # start MCP stdio server
specforge mcp-config <path>   # print Claude Code settings.json snippet
```

## Configuration file (.specforge.yaml)

```yaml
project_name: "My Project"
git_commit: false        # auto-commit every write

llm:
  provider: anthropic    # anthropic | openai | ollama
  model: ""              # default: claude-sonnet-4-6 / gpt-4o-mini / llama3.2
  api_key: ""            # falls back to ANTHROPIC_API_KEY / OPENAI_API_KEY env vars
  base_url: ""           # override endpoint; Ollama: http://localhost:11434

webhooks:
  - url: https://hooks.example.com/specforge
    events: [artifact.created, artifact.promoted]
    secret: "optional-hmac-secret"
```

## Web UI

Open `http://127.0.0.1:8765/ui` after starting `specforge-daemon`.

- **Project** — enter the project path and click **Open**, then use the
  toolbar buttons to rebuild the trace, view status, export, etc.
- **Create Artifact** — fill in kind, status, title, body, and optional
  link fields, then click **Create Artifact**.
- **Artifacts table** — click any row to auto-fill the Promote, Link, and
  Update Status panels.
- **Theme toggle** — ☀ Light / ⊙ System / ☾ Dark in the top-right corner.
