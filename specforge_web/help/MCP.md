# MCP Integration (Claude Code)

SpecForge exposes an **MCP (Model Context Protocol) server** so that
Claude Code can read and write artifacts directly during a conversation.
Claude can create requirements, draft tasks, promote ideas, and check
the release gate — all without leaving your editor.

---

## Setup

### 1. Start the MCP server

Point SpecForge at your project:

```bash
specforge mcp /path/to/my-project
```

This starts a JSON-RPC 2.0 server on `stdin/stdout` — the standard
MCP transport. Leave the terminal open, or configure it to start
automatically (see below).

### 2. Get the Claude Code config snippet

```bash
specforge mcp-config /path/to/my-project
```

Output:

```json
{
  "mcpServers": {
    "specforge": {
      "command": "/usr/local/bin/specforge",
      "args": ["mcp", "/path/to/my-project"]
    }
  }
}
```

### 3. Add to Claude Code settings

Open Claude Code settings (`Cmd/Ctrl+,`) and paste the `mcpServers`
block into `settings.json`. Reload Claude Code and the SpecForge
tools will appear in your session.

---

## Available MCP tools

| Tool | Description |
|------|-------------|
| `create_artifact` | Create a new artifact with kind, title, body, and links |
| `promote_artifact` | Promote an artifact to a new kind |
| `update_status` | Change an artifact's status |
| `get_artifact` | Retrieve a single artifact by ID |
| `list_artifacts` | List artifacts, optionally filtered by kind, status, or tag |
| `link_artifact` | Append links to an existing artifact |
| `unlink_artifact` | Remove links from an existing artifact |
| `search` | Full-text search across titles and bodies |
| `get_status` | Project health dashboard (gate, counts, open tasks) |
| `context_pack` | Full context pack: requirements, tasks, decisions |
| `validate` | Validate links and status consistency |

---

## Example Claude Code session

Once the MCP server is connected, you can ask Claude directly:

> "Add a requirement: the export function must handle files larger than
> 1 GB without loading them fully into memory."

> "Show me all open tasks tagged v2.0."

> "What's the current release gate status?"

> "Promote IDEA-0003 to a requirement with the title 'Batch export
> support' and link it to REQ-0001."

Claude will call the appropriate SpecForge MCP tools and show you the
results inline in the conversation.

---

## Context pack

The `context_pack` tool returns a structured summary of the project
suitable for giving Claude full context before planning work:

```json
{
  "project_name": "Drawing Export System",
  "artifact_count": 42,
  "approved_requirements": [...],
  "open_tasks": [...],
  "unverified_requirements": [...],
  "recent_decisions": [...]
}
```

You can also generate it from the CLI and feed it manually:

```bash
specforge context-pack ./proj --output context.json
# Then paste or attach context.json to your Claude conversation
```

---

## Daemon REST API

The full REST API (when `specforge-daemon` is running) can also be
used by AI tooling. Key endpoints:

```
POST   /projects/open          Open a project
POST   /artifacts              Create artifact
GET    /artifacts              List artifacts (?kind=&status=&tag=)
GET    /artifacts/{id}         Get artifact
POST   /artifacts/{id}/promote Promote artifact
PATCH  /artifacts/{id}/status  Update status
POST   /artifacts/{id}/link    Add links
POST   /artifacts/{id}/unlink  Remove links
GET    /search?q=              Full-text search
GET    /status                 Project dashboard
GET    /context-pack           AI context pack
GET    /report                 Acceptance report (Markdown)
GET    /validate               Validate project
POST   /tool-call              Generic AI adapter (action + params)
```

---

## Troubleshooting

**Tools don't appear in Claude Code** — check that the `command` path
in settings.json is the correct absolute path to the `specforge`
executable. Run `which specforge` to confirm.

**"Project not found"** — the `args` path in the MCP config must be
the absolute path to your project directory, not a relative path.

**Tool calls fail with "no project opened"** — the MCP server is
stateless; it opens the project specified in `args` automatically.
Check that the path exists and contains a `.specforge.yaml` or at
least the standard directory scaffold.
