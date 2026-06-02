"""Tests for specforge draft CLI command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from specforge_cli.main import app
from specforge_core.models import ArtifactKind
from specforge_core.project import Project


runner = CliRunner()


@patch("specforge_core.llm.urllib.request.urlopen")
def _mock_complete(mock_urlopen: MagicMock, body: str = "Generated body text") -> MagicMock:
    """Helper: configure urlopen to return a valid Anthropic response."""
    import json
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"content": [{"text": body}]}
    ).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp
    return mock_urlopen


class TestDraftCommand:
    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_draft_creates_artifact(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"content": [{"text": "## Purpose\nExport DXF files."}]}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        project = Project(tmp_path)
        project.init()
        from specforge_core.config import save_config, load_config
        from specforge_core.llm import LLMConfig
        cfg = load_config(tmp_path)
        cfg.llm = LLMConfig(provider="anthropic", api_key="sk-test")
        save_config(tmp_path, cfg)

        result = runner.invoke(
            app,
            ["draft", str(tmp_path), "requirement",
             "Export DXF files compatible with AutoCAD 2018",
             "--no-confirm"],
        )
        assert result.exit_code == 0, result.output
        assert "REQ-0001" in result.output

        artifacts = project.artifacts()
        assert len(artifacts) == 1
        assert artifacts[0].kind == ArtifactKind.REQUIREMENT
        assert "Export DXF" in artifacts[0].body

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_draft_uses_prompt_as_title(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"content": [{"text": "body"}]}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        project = Project(tmp_path)
        project.init()
        from specforge_core.config import save_config, load_config
        from specforge_core.llm import LLMConfig
        cfg = load_config(tmp_path)
        cfg.llm = LLMConfig(provider="anthropic", api_key="sk-test")
        save_config(tmp_path, cfg)

        result = runner.invoke(
            app,
            ["draft", str(tmp_path), "idea", "Short prompt", "--no-confirm"],
        )
        assert result.exit_code == 0
        artifacts = project.artifacts()
        assert artifacts[0].title == "Short prompt"

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_draft_explicit_title(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"content": [{"text": "body"}]}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        project = Project(tmp_path)
        project.init()
        from specforge_core.config import save_config, load_config
        from specforge_core.llm import LLMConfig
        cfg = load_config(tmp_path)
        cfg.llm = LLMConfig(provider="anthropic", api_key="sk-test")
        save_config(tmp_path, cfg)

        result = runner.invoke(
            app,
            ["draft", str(tmp_path), "idea", "some prompt",
             "--title", "My Custom Title", "--no-confirm"],
        )
        assert result.exit_code == 0
        artifacts = project.artifacts()
        assert artifacts[0].title == "My Custom Title"

    def test_draft_unknown_kind_exits_1(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        result = runner.invoke(
            app,
            ["draft", str(tmp_path), "nonexistent-kind", "some prompt"],
        )
        assert result.exit_code == 1
        assert "Unknown artifact kind" in result.output

    def test_draft_llm_error_exits_1(self, tmp_path: Path) -> None:
        project = Project(tmp_path)
        project.init()
        # No API key → LLMError; runner sends "N" to the fallback prompt
        result = runner.invoke(
            app,
            ["draft", str(tmp_path), "idea", "some prompt", "--no-confirm"],
            input="N\n",
        )
        assert result.exit_code == 1
        assert "LLM error" in result.output

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_draft_with_tag(
        self, mock_urlopen: MagicMock, tmp_path: Path
    ) -> None:
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"content": [{"text": "body"}]}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        project = Project(tmp_path)
        project.init()
        from specforge_core.config import save_config, load_config
        from specforge_core.llm import LLMConfig
        cfg = load_config(tmp_path)
        cfg.llm = LLMConfig(provider="anthropic", api_key="sk-test")
        save_config(tmp_path, cfg)

        result = runner.invoke(
            app,
            ["draft", str(tmp_path), "idea", "prompt",
             "--tag", "v1.0", "--no-confirm"],
        )
        assert result.exit_code == 0
        artifacts = project.artifacts()
        assert "v1.0" in artifacts[0].tags
