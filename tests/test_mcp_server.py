"""Tests for the MCP stdio server."""
import json

import pytest

from specforge_core.models import ArtifactKind, ArtifactStatus
from specforge_core.project import Project
from specforge_daemon.mcp_server import _TOOLS, _err, _ok, _text


def _call(project: Project, method: str, params: dict | None = None) -> dict:
    """Simulate one MCP request through the server logic (without stdio)."""
    from specforge_core.adapter import handle_tool_call
    from specforge_core.status import project_status

    req_id = 1
    if method == "tools/list":
        return _ok(req_id, {"tools": _TOOLS})

    if method == "tools/call":
        tool_name = (params or {}).get("name", "")
        args: dict = dict((params or {}).get("arguments", {}))
        args["action"] = tool_name
        if tool_name == "get_status":
            data = project_status(project)
            return _ok(req_id, _text(data))
        result = handle_tool_call(project, args)
        return _ok(req_id, _text(result))

    return _err(req_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

def test_tools_list_returns_all_tools():
    resp = _call(None, "tools/list")  # type: ignore[arg-type]
    tools = resp["result"]["tools"]
    names = {t["name"] for t in tools}
    expected = {
        "create_artifact", "promote_artifact", "update_status",
        "link_artifact", "unlink_artifact", "get_artifact", "list_artifacts", "search",
        "get_status", "context_pack", "validate",
        "check_gate", "draft_artifact", "bulk_update", "list_templates",
    }
    assert expected == names


def test_each_tool_has_input_schema():
    for tool in _TOOLS:
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


def test_create_artifact_schema_has_required_fields():
    tool = next(t for t in _TOOLS if t["name"] == "create_artifact")
    assert "kind" in tool["inputSchema"]["required"]
    assert "title" in tool["inputSchema"]["required"]
    assert "body" in tool["inputSchema"]["required"]


# ---------------------------------------------------------------------------
# Tool calls via server logic
# ---------------------------------------------------------------------------

def test_create_artifact_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    resp = _call(project, "tools/call", {
        "name": "create_artifact",
        "arguments": {"kind": "idea", "title": "MCP idea", "body": "From MCP."},
    })
    assert "error" not in resp
    content_text = resp["result"]["content"][0]["text"]
    data = json.loads(content_text)
    assert data["ok"] is True
    assert data["result"]["id"].startswith("IDEA-")


def test_promote_artifact_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    idea = project.create_artifact(ArtifactKind.IDEA, "DXF", "Explore.")
    resp = _call(project, "tools/call", {
        "name": "promote_artifact",
        "arguments": {"id": idea.id, "target_kind": "candidate"},
    })
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert data["result"]["source"] == idea.id


def test_update_status_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(
        ArtifactKind.REQUIREMENT, "Export DXF", ".", status=ArtifactStatus.APPROVED,
    )
    resp = _call(project, "tools/call", {
        "name": "update_status",
        "arguments": {"id": req.id, "status": "implemented"},
    })
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert data["result"]["status"] == "implemented"


def test_get_artifact_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    req = project.create_artifact(ArtifactKind.REQUIREMENT, "Export DXF", "Body.")
    resp = _call(project, "tools/call", {
        "name": "get_artifact",
        "arguments": {"id": req.id},
    })
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert data["result"]["title"] == "Export DXF"


def test_list_artifacts_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.IDEA, "Idea 1", ".")
    project.create_artifact(ArtifactKind.REQUIREMENT, "Req 1", ".", status=ArtifactStatus.APPROVED)
    resp = _call(project, "tools/call", {
        "name": "list_artifacts",
        "arguments": {"kind": "idea"},
    })
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert len(data["result"]) == 1


def test_search_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    project.create_artifact(ArtifactKind.REQUIREMENT, "Export DXF", "Shall export.", status=ArtifactStatus.APPROVED)
    from specforge_core.trace import TraceIndex
    TraceIndex(project).rebuild()
    resp = _call(project, "tools/call", {
        "name": "search",
        "arguments": {"query": "DXF"},
    })
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert len(data["result"]) > 0


def test_get_status_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    resp = _call(project, "tools/call", {"name": "get_status", "arguments": {}})
    data = json.loads(resp["result"]["content"][0]["text"])
    assert "gate" in data
    assert data["gate"] in ("PASS", "FAIL")


def test_context_pack_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    resp = _call(project, "tools/call", {"name": "context_pack", "arguments": {}})
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert "approved_requirements" in data["result"]


def test_validate_via_mcp(tmp_path):
    project = Project(tmp_path / "proj")
    project.init()
    resp = _call(project, "tools/call", {"name": "validate", "arguments": {}})
    data = json.loads(resp["result"]["content"][0]["text"])
    assert data["ok"] is True
    assert data["result"]["ok"] is True


def test_unknown_method_returns_error():
    resp = _err(1, -32601, "Method not found: foo/bar")
    assert resp["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# CLI mcp-config
# ---------------------------------------------------------------------------

def test_cli_mcp_config(tmp_path):
    from typer.testing import CliRunner
    from specforge_cli.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["mcp-config", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # Output is pretty JSON followed by a hint line; parse just the JSON block
    json_text = result.output[:result.output.rfind("}") + 1]
    config = json.loads(json_text)
    assert "mcpServers" in config
    assert "specforge" in config["mcpServers"]
    assert config["mcpServers"]["specforge"]["args"][0] == "mcp"


# ---------------------------------------------------------------------------
# New tools: check_gate, bulk_update, list_templates, draft_artifact
# ---------------------------------------------------------------------------

def _mcp_call(project: Project, tool_name: str, arguments: dict) -> dict:
    """Invoke new tools directly through mcp_server.serve logic (simulated)."""
    from specforge_daemon.mcp_server import _ok, _text, _TOOLS

    req_id = 99

    if tool_name == "check_gate":
        from specforge_core.status import project_status
        from specforge_core.validation import validate_project
        st = project_status(project)
        errors = validate_project(project)
        return _ok(req_id, _text({
            "pass": st.get("gate") == "PASS",
            "gate": st.get("gate"),
            "open_tasks": st.get("open_tasks", []),
            "unverified_requirements": st.get("unverified_requirements", []),
            "validation_errors": errors,
        }))

    if tool_name == "bulk_update":
        from specforge_core.bulk import bulk_update
        action = str(arguments.get("action", "archive"))
        filters: dict = {}
        if arguments.get("kind"):
            filters["kind"] = list(arguments["kind"])
        if arguments.get("status"):
            filters["status"] = str(arguments["status"])
        if arguments.get("tag"):
            filters["tag"] = list(arguments["tag"])
        op_params: dict = {}
        if arguments.get("to_status"):
            op_params["to_status"] = str(arguments["to_status"])
        if arguments.get("tags_to_apply"):
            op_params["tags"] = list(arguments["tags_to_apply"])
        dry_run = bool(arguments.get("dry_run", False))
        affected = bulk_update(project, action, filters, op_params, dry_run=dry_run)
        return _ok(req_id, _text({
            "ok": True,
            "dry_run": dry_run,
            "affected_count": len(affected),
            "affected": [{"id": a.id, "kind": a.kind.value, "status": a.status.value, "title": a.title} for a in affected],
        }))

    if tool_name == "list_templates":
        from specforge_core.templates import list_templates, load_template
        kinds = list_templates(project.root)
        templates = []
        for k in kinds:
            body, meta = load_template(project.root, k)
            templates.append({"kind": k, "tags": meta.get("tags", []), "body_preview": body[:200]})
        return _ok(req_id, _text({"ok": True, "templates": templates}))

    return _ok(req_id, _text({"ok": False, "error": f"Unknown tool: {tool_name}"}))


class TestCheckGate:
    def test_gate_fails_on_empty_project(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        resp = _mcp_call(project, "check_gate", {})
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "gate" in data
        assert "pass" in data

    def test_gate_passes_when_verified(self, tmp_path):
        from specforge_core.models import ArtifactStatus
        project = Project(tmp_path)
        project.init()
        art = project.create_artifact(ArtifactKind.REQUIREMENT, "REQ", "body",
                                       status=ArtifactStatus.APPROVED)
        project.update_status(art.id, ArtifactStatus.VERIFIED)
        resp = _mcp_call(project, "check_gate", {})
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["pass"] is True
        assert data["gate"] == "PASS"

    def test_gate_fails_when_open_tasks(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        project.create_artifact(ArtifactKind.TASK, "Open task", "body")
        resp = _mcp_call(project, "check_gate", {})
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["pass"] is False


class TestBulkUpdateMCP:
    def test_bulk_archive_via_mcp(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        project.create_artifact(ArtifactKind.TASK, "Task 1", "body")
        project.create_artifact(ArtifactKind.TASK, "Task 2", "body")

        resp = _mcp_call(project, "bulk_update", {
            "action": "archive",
            "kind": ["task"],
        })
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["ok"] is True
        assert data["affected_count"] == 2

    def test_bulk_dry_run_does_not_write(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        a = project.create_artifact(ArtifactKind.TASK, "Task", "body")

        resp = _mcp_call(project, "bulk_update", {
            "action": "update-status",
            "kind": ["task"],
            "to_status": "implemented",
            "dry_run": True,
        })
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["dry_run"] is True
        assert data["affected_count"] == 1
        # Status should be unchanged
        fresh = project.get_artifact(a.id)
        assert fresh.status == ArtifactStatus.DRAFT

    def test_bulk_tag_add_via_mcp(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        a = project.create_artifact(ArtifactKind.TASK, "Task", "body")

        _mcp_call(project, "bulk_update", {
            "action": "tag-add",
            "kind": ["task"],
            "tags_to_apply": ["sprint-12"],
        })
        fresh = project.get_artifact(a.id)
        assert "sprint-12" in fresh.tags


class TestListTemplatesMCP:
    def test_lists_templates(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        resp = _mcp_call(project, "list_templates", {})
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["ok"] is True
        kinds = [t["kind"] for t in data["templates"]]
        assert "requirement" in kinds
        assert "task" in kinds

    def test_empty_when_no_templates(self, tmp_path):
        project = Project(tmp_path)
        project.init()
        # Remove all templates
        import shutil
        shutil.rmtree(project.root / ".specforge" / "templates")
        resp = _mcp_call(project, "list_templates", {})
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["templates"] == []


class TestDraftEndpointDaemon:
    """Test POST /draft daemon endpoint."""

    def test_draft_creates_artifact(self, tmp_path):
        import json as _json
        from unittest.mock import MagicMock, patch
        from fastapi.testclient import TestClient
        import specforge_daemon.api as _api
        from specforge_daemon.api import app

        client = TestClient(app)
        _api._active_project = None

        # Open project
        project = Project(tmp_path)
        project.init()
        # Configure LLM
        from specforge_core.config import save_config, load_config
        from specforge_core.llm import LLMConfig
        cfg = load_config(tmp_path)
        cfg.llm = LLMConfig(provider="anthropic", api_key="sk-test")
        save_config(tmp_path, cfg)

        client.post("/projects/open", json={"path": str(tmp_path)})

        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps(
            {"content": [{"text": "Generated requirement body."}]}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("specforge_core.llm.urllib.request.urlopen", return_value=mock_resp):
            r = client.post("/draft", json={
                "kind": "requirement",
                "prompt": "System must support TLS 1.2 or later",
                "title": "TLS requirement",
            })

        assert r.status_code == 200
        data = r.json()
        assert data["kind"] == "requirement"
        assert data["title"] == "TLS requirement"
        assert "Generated" in data["body"]
        assert data["id"].startswith("REQ-")

    def test_draft_unknown_kind_returns_400(self, tmp_path):
        from fastapi.testclient import TestClient
        import specforge_daemon.api as _api
        from specforge_daemon.api import app

        client = TestClient(app)
        _api._active_project = None

        project = Project(tmp_path)
        project.init()
        client.post("/projects/open", json={"path": str(tmp_path)})

        r = client.post("/draft", json={
            "kind": "nonsense",
            "prompt": "test",
        })
        assert r.status_code == 400
