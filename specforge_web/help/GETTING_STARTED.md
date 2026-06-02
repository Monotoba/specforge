# Getting Started with SpecForge

SpecForge is a **local-first requirements engineering system** for
software and hardware projects. It keeps every artifact of a project —
ideas, requirements, decisions, tasks, tests, and verification evidence
— as plain Markdown files in a directory you control, with a SQLite
index for fast queries and full traceability between everything.

Nothing leaves your machine unless you push to git. No account
required, no cloud service, no vendor lock-in.

---

## What problem does SpecForge solve?

Most teams track work in one tool and requirements in another — or
nowhere at all. When a bug reaches production, nobody can quickly answer:
*what requirement said this should work this way, who approved it, what
test was supposed to catch this, and was that test ever run?*

SpecForge creates a traceable thread from every user need through the
formal requirement, the task that implements it, and the test that
proves it works. Every link is recorded. The release gate refuses to
let you ship until every requirement has documented verification
evidence.

---

## Installation

```bash
pip install -e /path/to/specforge --break-system-packages
```

Or with all extras:

```bash
pip install -e ".[dev,desktop]" --break-system-packages
```

---

## Your first project: five minutes

### 1. Create a project

```bash
specforge init ./my-project --git --name "My Project"
```

This creates the directory scaffold, initialises git, and writes a
commented `.specforge.yaml` configuration file.

### 2. Capture an idea

```bash
specforge add-idea ./my-project "Dark mode support" \
  "Users need a dark colour scheme to reduce eye strain during
  extended use. Requested by 3 customers this month."
```

### 3. Promote to a requirement

When the idea is solid enough to commit to:

```bash
specforge promote ./my-project IDEA-0001 requirement \
  --text "The application shall provide a dark colour mode that
  reduces bright white backgrounds. The mode shall be togglable
  via a button in the header. The selection shall persist across
  sessions via localStorage."
```

### 4. Create a task and link it

```bash
specforge add-task ./my-project "Implement dark mode" \
  --text "Add CSS custom property theming. Implement theme toggle
  button in header. Persist choice in localStorage. Test across
  Chrome, Firefox, Safari." \
  --implements REQ-0001 --git
```

### 5. Mark implemented and add verification evidence

```bash
specforge update-status ./my-project TASK-0001 implemented
specforge update-status ./my-project REQ-0001 implemented

specforge add-test ./my-project "Dark mode toggle" \
  --text "Click toggle. Verify background changes to #18181b.
  Reload page. Verify dark mode persists." \
  --req REQ-0001

specforge add-verification ./my-project "Dark mode — QA passed" \
  --text "Manual QA: Chrome 124, Firefox 125, Safari 17.
  All three themes apply correctly. Persistence verified." \
  --req REQ-0001 --test TEST-0001 --git

specforge update-status ./my-project REQ-0001 verified --git
```

### 6. Check the release gate

```bash
specforge check ./my-project
# Release Gate: PASS ✅
```

---

## Understanding the lifecycle

Every artifact moves through a lifecycle. Requirements follow this path:

```
draft → proposed → approved → implemented → verified
```

The **release gate** checks that every approved requirement is
`verified` and there are no open tasks. Until both conditions are met,
the project is not ready to ship.

The gate is binary and intentional: either every requirement is verified
with documented evidence, or it is not. There is no partial pass.

---

## Using AI drafting

Configure your LLM provider once per project:

```bash
specforge config ./my-project --set llm.provider=anthropic
# Reads ANTHROPIC_API_KEY environment variable automatically
```

Then draft artifact bodies from plain English:

```bash
specforge draft ./my-project requirement \
  "All API endpoints must require authentication — no anonymous access
  to any resource except the login endpoint"
```

SpecForge calls the LLM, shows you the generated body, and asks for
confirmation. Press Enter to accept or `n` to discard.

If you prefer local AI with no internet or API costs, use Ollama:

```bash
# Install Ollama from ollama.com, then:
ollama pull llama3.2
specforge config ./my-project --set llm.provider=ollama
```

---

## The web UI

Start the daemon and open the web interface:

```bash
specforge-daemon
# Open http://127.0.0.1:8765/ui
```

The web UI supports **dark, light, and system colour modes** — toggle
with the ☀/⊙/☾ buttons in the top-right corner. Dark mode uses muted
indigo accents on a charcoal background, designed for extended use and
sensitive eyes.

Click **? Help** at any time for built-in documentation.

---

## Next steps

- **Workflow** — understand the five-phase process: Explore, Specify,
  Implement, Verify, Release
- **Artifact Types** — learn what each of the 12 artifact kinds is for
- **AI Drafting** — configure all three LLM providers and use Ollama
  for offline work
- **MCP / Claude Code** — connect SpecForge to Claude Code so your AI
  assistant can read and write your project during development
- **Tutorials** — see [docs/tutorials/](../docs/tutorials/) for
  complete worked examples

Full documentation: [README.md](../README.md)
