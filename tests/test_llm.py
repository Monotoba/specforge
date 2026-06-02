"""Tests for specforge_core/llm.py — LLM client abstraction."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specforge_core.llm import (
    LLMConfig,
    LLMError,
    _DRAFT_SYSTEM,
    complete,
    complete_with_fallback,
)


class TestLLMConfig:
    def test_defaults(self) -> None:
        cfg = LLMConfig()
        assert cfg.provider == "anthropic"
        assert cfg.model == ""
        assert cfg.api_key == ""
        assert cfg.base_url == ""

    def test_effective_model_falls_back_to_default(self) -> None:
        assert LLMConfig(provider="anthropic").effective_model() == "claude-sonnet-4-6"
        assert LLMConfig(provider="openai").effective_model() == "gpt-4o-mini"
        assert LLMConfig(provider="ollama").effective_model() == "llama3.2"

    def test_effective_model_uses_explicit(self) -> None:
        cfg = LLMConfig(provider="anthropic", model="claude-opus-4-7")
        assert cfg.effective_model() == "claude-opus-4-7"

    def test_effective_base_url_defaults(self) -> None:
        assert "api.anthropic.com" in LLMConfig(provider="anthropic").effective_base_url()
        assert "localhost:11434" in LLMConfig(provider="ollama").effective_base_url()

    def test_effective_api_key_explicit(self) -> None:
        cfg = LLMConfig(provider="anthropic", api_key="sk-explicit")
        assert cfg.effective_api_key() == "sk-explicit"

    def test_effective_api_key_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
        cfg = LLMConfig(provider="anthropic")
        assert cfg.effective_api_key() == "sk-env-key"

    def test_effective_api_key_openai_env(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        cfg = LLMConfig(provider="openai")
        assert cfg.effective_api_key() == "sk-openai"

    def test_effective_api_key_ollama_no_key_needed(self) -> None:
        cfg = LLMConfig(provider="ollama")
        assert cfg.effective_api_key() == ""

    def test_unknown_provider_raises(self) -> None:
        cfg = LLMConfig(provider="unknown")
        with pytest.raises(LLMError, match="Unknown provider"):
            complete("prompt", "system", cfg)


def _make_urlopen_mock(response_body: dict):
    """Return a mock for urllib.request.urlopen that returns response_body as JSON."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_body).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen = MagicMock(return_value=mock_resp)
    return mock_urlopen


class TestCompleteAnthropic:
    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_posts_to_messages_endpoint(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"content": [{"text": "Generated body"}]}
        )
        cfg = LLMConfig(provider="anthropic", api_key="sk-test")
        result = complete("my prompt", "system", cfg)
        assert result == "Generated body"
        call_args = mock_urlopen.call_args[0][0]
        assert "messages" in call_args.full_url
        assert "api.anthropic.com" in call_args.full_url

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_includes_api_key_header(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"content": [{"text": "body"}]}
        )
        cfg = LLMConfig(provider="anthropic", api_key="sk-mykey")
        complete("prompt", "system", cfg)
        req = mock_urlopen.call_args[0][0]
        # urllib lowercases header names
        headers_lower = {k.lower(): v for k, v in req.headers.items()}
        assert headers_lower.get("x-api-key") == "sk-mykey"

    def test_raises_llmerror_without_api_key(self) -> None:
        cfg = LLMConfig(provider="anthropic", api_key="")
        with pytest.raises(LLMError, match="No API key"):
            complete("prompt", "system", cfg)

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_raises_llmerror_on_http_error(self, mock_urlopen: MagicMock) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="url", code=401, msg="Unauthorized",
            hdrs=MagicMock(), fp=MagicMock(read=lambda: b"Unauthorized"),
        )
        cfg = LLMConfig(provider="anthropic", api_key="sk-bad")
        with pytest.raises(LLMError, match="HTTP 401"):
            complete("prompt", "system", cfg)


class TestCompleteOpenAI:
    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_posts_to_chat_completions(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"choices": [{"message": {"content": "OpenAI body"}}]}
        )
        cfg = LLMConfig(provider="openai", api_key="sk-openai")
        result = complete("prompt", "system", cfg)
        assert result == "OpenAI body"
        req = mock_urlopen.call_args[0][0]
        assert "chat/completions" in req.full_url

    def test_raises_llmerror_without_api_key(self) -> None:
        cfg = LLMConfig(provider="openai", api_key="")
        with pytest.raises(LLMError, match="No API key"):
            complete("prompt", "system", cfg)


class TestCompleteOllama:
    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_posts_to_api_chat(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"message": {"content": "Ollama body"}}
        )
        cfg = LLMConfig(provider="ollama")
        result = complete("prompt", "system", cfg)
        assert result == "Ollama body"
        req = mock_urlopen.call_args[0][0]
        assert "localhost:11434" in req.full_url
        assert "/api/chat" in req.full_url

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_sets_stream_false(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"message": {"content": "body"}}
        )
        cfg = LLMConfig(provider="ollama")
        complete("prompt", "system", cfg)
        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        assert payload["stream"] is False


class TestCompleteWithFallback:
    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_succeeds_without_fallback(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"content": [{"text": "primary result"}]}
        )
        cfg = LLMConfig(provider="anthropic", api_key="sk-test")
        ask_fallback = MagicMock(return_value=False)
        result = complete_with_fallback("p", "s", cfg, ask_fallback)
        assert result == "primary result"
        ask_fallback.assert_not_called()

    def test_calls_ask_fallback_on_error(self) -> None:
        cfg = LLMConfig(provider="anthropic", api_key="")  # will raise LLMError
        ask_fallback = MagicMock(return_value=False)
        with pytest.raises(LLMError):
            complete_with_fallback("p", "s", cfg, ask_fallback)
        ask_fallback.assert_called_once()
        # error message should be in the call arg
        assert "API key" in ask_fallback.call_args[0][0]

    @patch("specforge_core.llm.urllib.request.urlopen")
    def test_retries_with_ollama_when_fallback_accepted(
        self, mock_urlopen: MagicMock
    ) -> None:
        mock_urlopen.side_effect = _make_urlopen_mock(
            {"message": {"content": "ollama result"}}
        )
        cfg = LLMConfig(provider="anthropic", api_key="")  # triggers LLMError
        ask_fallback = MagicMock(return_value=True)
        result = complete_with_fallback("p", "s", cfg, ask_fallback)
        assert result == "ollama result"
        # Verify Ollama endpoint was called
        req = mock_urlopen.call_args[0][0]
        assert "localhost:11434" in req.full_url

    def test_reraises_when_fallback_declined(self) -> None:
        cfg = LLMConfig(provider="anthropic", api_key="")
        ask_fallback = MagicMock(return_value=False)
        with pytest.raises(LLMError):
            complete_with_fallback("p", "s", cfg, ask_fallback)

    def test_draft_system_prompt_exported(self) -> None:
        assert isinstance(_DRAFT_SYSTEM, str)
        assert len(_DRAFT_SYSTEM) > 20
