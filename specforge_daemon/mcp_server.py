"""MCP stdio server — exposes SpecForge as a Claude Code / MCP tool.

Run via:
    specforge mcp /path/to/project

Then register it in Claude Code settings as:
    specforge mcp-config /path/to/project

Protocol: JSON-RPC 2.0 over stdin/stdout (MCP stdio transport).
Supported MCP methods: initialize, tools/list, tools/call.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from specforge_core.adapter import handle_tool_call
from specforge_core.project import Project

_TOOLS = [
    {
        "name": "create_artifact",
        "description": "Create a SpecForge artifact (idea, requirement, task, test, etc.).",
        "inputSchema": {
            "type": "object",
            "required": ["kind", "title", "body"],
            "properties": {
                "kind": {"type": "string", "enum": [
                    "idea", "candidate", "requirement", "decision", "assumption",
                    "constraint", "change_order", "task", "test", "verification",
                    "reference", "conversation",
                ]},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "status": {"type": "string", "enum": [
                    "draft", "proposed", "approved", "implemented", "verified",
                    "rejected", "archived",
                ]},
                "source": {"type": "string", "description": "Source artifact ID"},
                "implements": {"type": "array", "items": {"type": "string"},
                               "description": "Requirement IDs this task implements"},
                "related_requirements": {"type": "array", "items": {"type": "string"}},
                "depends_on": {"type": "array", "items": {"type": "string"}},
                "verified_by": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "git_commit": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "promote_artifact",
        "description": "Promote an artifact to a new kind, creating a trace link.",
        "inputSchema": {
            "type": "object",
            "required": ["id", "target_kind"],
            "properties": {
                "id": {"type": "string"},
                "target_kind": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "git_commit": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "update_status",
        "description": "Update the status of an existing artifact.",
        "inputSchema": {
            "type": "object",
            "required": ["id", "status"],
            "properties": {
                "id": {"type": "string"},
                "status": {"type": "string", "enum": [
                    "draft", "proposed", "approved", "implemented", "verified",
                    "rejected", "archived",
                ]},
                "git_commit": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "unlink_artifact",
        "description": "Remove specific links from an existing artifact. Only the listed IDs are removed; others are preserved.",
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "implements": {"type": "array", "items": {"type": "string"}},
                "related_requirements": {"type": "array", "items": {"type": "string"}},
                "verified_by": {"type": "array", "items": {"type": "string"}},
                "depends_on": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "clear_source": {"type": "boolean", "default": False},
                "git_commit": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "link_artifact",
        "description": "Append links to an existing artifact (implements, related requirements, verified-by, tags, etc.). Existing links are preserved; duplicates are ignored.",
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "implements": {"type": "array", "items": {"type": "string"}},
                "related_requirements": {"type": "array", "items": {"type": "string"}},
                "verified_by": {"type": "array", "items": {"type": "string"}},
                "depends_on": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "git_commit": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "get_artifact",
        "description": "Retrieve a single artifact by ID.",
        "inputSchema": {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
        },
    },
    {
        "name": "list_artifacts",
        "description": "List artifacts with optional kind, status, and tag filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "status": {"type": "string"},
                "tag": {"type": "string"},
            },
        },
    },
    {
        "name": "search",
        "description": "Full-text search across artifact titles and bodies. All terms must match.",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "kinds": {"type": "array", "items": {"type": "string"}},
                "statuses": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "get_status",
        "description": "Project health dashboard: artifact counts, open tasks, unverified requirements, release gate.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "context_pack",
        "description": "Build an AI context bundle with approved requirements, open tasks, decisions, and links.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "validate",
        "description": "Check project referential integrity. Returns ok=true and a list of errors.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_gate",
        "description": "Check the release gate. Returns pass=true only when all requirements are verified and there are no open tasks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "draft_artifact",
        "description": "Generate an artifact body using the configured LLM (Anthropic/OpenAI/Ollama) from a plain-language prompt, then create the artifact immediately. No confirmation prompt in MCP mode.",
        "inputSchema": {
            "type": "object",
            "required": ["kind", "prompt"],
            "properties": {
                "kind": {"type": "string", "enum": [
                    "idea", "candidate", "requirement", "decision", "assumption",
                    "constraint", "change_order", "task", "test", "verification",
                    "reference", "conversation",
                ]},
                "prompt": {"type": "string", "description": "Plain-language description of what to generate"},
                "title": {"type": "string", "description": "Artifact title (defaults to first 60 chars of prompt)"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "git_commit": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "bulk_update",
        "description": "Apply an action to all artifacts matching kind/status/tag filters. Use dry_run=true to preview without writing.",
        "inputSchema": {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": ["update-status", "archive", "tag-add", "tag-remove"]},
                "kind": {"type": "array", "items": {"type": "string"}, "description": "Filter by kind(s)"},
                "status": {"type": "string", "description": "Filter by current status"},
                "tag": {"type": "array", "items": {"type": "string"}, "description": "Filter: all tags must match"},
                "to_status": {"type": "string", "description": "Target status for update-status action"},
                "tags_to_apply": {"type": "array", "items": {"type": "string"}, "description": "Tags to add/remove"},
                "dry_run": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "list_templates",
        "description": "List available artifact templates in .specforge/templates/. Returns kind names and template body previews.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _ok(req_id: Any, result: object) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _text(content: object) -> dict[str, object]:
    return {"content": [{"type": "text", "text": json.dumps(content, default=str, indent=2)}]}


def serve(project_path: str) -> None:
    project = Project(project_path)
    project.init()

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            req = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method", "")

        if method == "initialize":
            response = _ok(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "specforge", "version": "0.20.0"},
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            response = _ok(req_id, {"tools": _TOOLS})
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name", "")
            args: dict[str, object] = dict(params.get("arguments", {}))

            if tool_name == "get_status":
                from specforge_core.status import project_status
                try:
                    data: object = project_status(project)
                    response = _ok(req_id, _text(data))
                except Exception as exc:
                    response = _ok(req_id, _text({"ok": False, "error": str(exc)}))

            elif tool_name == "check_gate":
                from specforge_core.status import project_status
                from specforge_core.validation import validate_project
                try:
                    st = project_status(project)
                    errors = validate_project(project)
                    gate_pass = (st.get("gate") == "PASS")
                    response = _ok(req_id, _text({
                        "pass": gate_pass,
                        "gate": st.get("gate"),
                        "open_tasks": st.get("open_tasks", []),
                        "unverified_requirements": st.get("unverified_requirements", []),
                        "validation_errors": errors,
                    }))
                except Exception as exc:
                    response = _ok(req_id, _text({"ok": False, "error": str(exc)}))

            elif tool_name == "draft_artifact":
                from specforge_core.llm import LLMError, _DRAFT_SYSTEM, complete_with_fallback
                from specforge_core.models import ArtifactKind
                try:
                    kind_val = str(args.get("kind", "idea"))
                    prompt = str(args.get("prompt", ""))
                    title = str(args.get("title") or prompt[:60].rstrip())
                    tags = list(args.get("tags") or [])
                    git_commit = bool(args.get("git_commit", False))
                    artifact_kind = ArtifactKind(kind_val)
                    system = _DRAFT_SYSTEM + f"\n\nArtifact kind: {artifact_kind.value}"
                    # In MCP mode there is no interactive fallback — propagate error
                    body = complete_with_fallback(
                        prompt, system, project.config.llm,
                        ask_fallback=lambda msg: False,
                    )
                    artifact = project.create_artifact(
                        artifact_kind, title, body,
                        git_commit=git_commit or project.config.git_commit,
                        tags=tags or None,
                    )
                    response = _ok(req_id, _text({
                        "ok": True,
                        "id": artifact.id,
                        "kind": artifact.kind.value,
                        "title": artifact.title,
                        "body": artifact.body,
                        "tags": artifact.tags,
                    }))
                except LLMError as exc:
                    response = _ok(req_id, _text({"ok": False, "error": f"LLM error: {exc}"}))
                except Exception as exc:
                    response = _ok(req_id, _text({"ok": False, "error": str(exc)}))

            elif tool_name == "bulk_update":
                from specforge_core.bulk import bulk_update
                try:
                    action = str(args.get("action", "archive"))
                    filters: dict[str, object] = {}
                    if args.get("kind"):
                        filters["kind"] = list(args["kind"])  # type: ignore[arg-type]
                    if args.get("status"):
                        filters["status"] = str(args["status"])
                    if args.get("tag"):
                        filters["tag"] = list(args["tag"])  # type: ignore[arg-type]
                    op_params: dict[str, object] = {}
                    if args.get("to_status"):
                        op_params["to_status"] = str(args["to_status"])
                    if args.get("tags_to_apply"):
                        op_params["tags"] = list(args["tags_to_apply"])  # type: ignore[arg-type]
                    dry_run = bool(args.get("dry_run", False))
                    affected = bulk_update(project, action, filters, op_params, dry_run=dry_run)
                    response = _ok(req_id, _text({
                        "ok": True,
                        "dry_run": dry_run,
                        "affected_count": len(affected),
                        "affected": [
                            {"id": a.id, "kind": a.kind.value,
                             "status": a.status.value, "title": a.title}
                            for a in affected
                        ],
                    }))
                except Exception as exc:
                    response = _ok(req_id, _text({"ok": False, "error": str(exc)}))

            elif tool_name == "list_templates":
                from specforge_core.templates import list_templates, load_template
                try:
                    kinds = list_templates(project.root)
                    templates = []
                    for k in kinds:
                        body, meta = load_template(project.root, k)
                        templates.append({
                            "kind": k,
                            "tags": meta.get("tags", []),
                            "body_preview": body[:200] + ("…" if len(body) > 200 else ""),
                        })
                    response = _ok(req_id, _text({"ok": True, "templates": templates}))
                except Exception as exc:
                    response = _ok(req_id, _text({"ok": False, "error": str(exc)}))

            else:
                args["action"] = tool_name
                result = handle_tool_call(project, args)
                response = _ok(req_id, _text(result))
        else:
            response = _err(req_id, -32601, f"Method not found: {method}")

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
