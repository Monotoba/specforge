# AI Integration Guide

SpecForge is designed to work alongside AI assistants at multiple
levels of integration, from simple context sharing to full bidirectional
tool use.

---

## Integration modes

### 1. Context pack (read-only, manual)

The simplest integration: export a structured project summary and
share it with any AI assistant.

```bash
specforge context-pack ./proj --output context.json
```

The context pack contains approved requirements, open tasks, unverified
requirements, and recent decisions. Attach it to a conversation and ask:

- "Review these requirements for clarity and completeness."
- "Which requirements might conflict with each other?"
- "Suggest implementation tasks for REQ-0003."
- "What should I verify before shipping?"

### 2. AI drafting (write, human-confirmed)

`specforge draft` calls an LLM to generate artifact bodies from
plain-language prompts. The human reviews and confirms every artifact.

```bash
specforge draft ./proj requirement \
  "The search function must return results within 500ms for queries
  against a corpus of up to 100,000 documents" \
  --title "Search latency requirement"
```

See [AI_DRAFTING.md](../specforge_web/help/AI_DRAFTING.md) for
provider setup (Anthropic, OpenAI, Ollama).

### 3. MCP integration (bidirectional, agent-controlled)

The MCP server gives Claude Code full read/write access to the project.
The AI can create artifacts, search, check status, and promote
requirements without leaving the editor.

```bash
specforge mcp-config ./proj   # print Claude Code settings.json snippet
```

Available MCP tools: `create_artifact`, `promote_artifact`,
`update_status`, `get_artifact`, `list_artifacts`, `link_artifact`,
`unlink_artifact`, `search`, `get_status`, `context_pack`, `validate`.

### 4. REST API (programmatic)

Any AI agent can use the daemon REST API. The `/tool-call` endpoint
accepts a generic action dispatch:

```bash
curl -s http://127.0.0.1:8765/tool-call \
  -H "Content-Type: application/json" \
  -d '{"action": "create_artifact", "kind": "idea",
       "title": "New idea", "body": "Description"}'
```

---

## Design principle

AI tools work **through the artifact system**, not around it. The
adapter layer accepts structured action calls and returns structured
results. AI cannot silently modify requirements or bypass the normal
status lifecycle.

**Safety rule**: no artifact becomes authoritative without an explicit
status promotion. AI agents can create and propose; humans approve.
