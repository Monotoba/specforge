# Troubleshooting

## Daemon won't start

**"Address already in use"** — another instance is running on port 8765.
Stop the existing process (`pkill -f specforge-daemon`) or pass a different
port: `specforge-daemon --port 8766`.

**"ModuleNotFoundError: specforge_daemon"** — the package is not installed.
Run `pip install -e . --break-system-packages` from the project directory.

## Web UI shows "Error: …"

**"No project opened"** — click **Open** and enter the full path to your
project directory before using any other action.

**"404 Not Found"** — the daemon is not running, or you are connecting to the
wrong port. Start `specforge-daemon` and check the URL in your browser.

## AI drafting fails

**"No API key for Anthropic"** — set the environment variable:
```bash
export ANTHROPIC_API_KEY="sk-..."
```
Or store it in `.specforge.yaml`:
```yaml
llm:
  api_key: "sk-..."
```

**"Request failed"** — the remote provider may be unreachable. SpecForge
will ask if you want to retry with local Ollama. Install Ollama from
[ollama.com](https://ollama.com) and run `ollama pull llama3.2` once.

**To switch permanently to Ollama:**
```bash
specforge config ./my-project --set llm.provider=ollama
```

## Validation errors

**"Broken link: TASK-0001 references REQ-0099 but REQ-0099 does not exist"**
— an artifact references an ID that has been deleted or was typed
incorrectly. Fix with:
```bash
specforge unlink ./my-project TASK-0001 --implements REQ-0099
```

**"Requirement REQ-0001 is approved but has no tasks implementing it"**
— expected; add a task with `--implements REQ-0001`.

## Release gate fails

```
specforge check ./my-project
```

Common reasons:
- One or more requirements are not yet `verified`.
  Use `specforge status ./my-project` to see which.
- There are open tasks (status `draft`, `proposed`, or `implemented`).
  Archive them: `specforge bulk ./my-project archive --kind task --status implemented`.

## Git commits fail

**"Not a git repository"** — the project was not initialised with `--git`.
Run `git init` inside the project folder and then `git add .` and
`git commit -m "initial"` to set up the history.

**Hook rejected push** — your repo has a pre-commit or pre-push hook that
is failing. Check the hook output and fix the underlying issue; do not
bypass hooks with `--no-verify`.

## Plugin errors

Plugin exceptions are caught and printed to `stderr` — the artifact mutation
still completes. To debug a plugin, check stderr output or add `print()`
calls to your plugin file. Plugins live in `.specforge/plugins/*.py`.

## Trace index is stale

Click **Rebuild Trace** in the web UI or run:
```bash
specforge trace ./my-project
```

The trace index is SQLite-backed and is excluded from git (`.gitignore`).
Rebuilding it is always safe and fast.
