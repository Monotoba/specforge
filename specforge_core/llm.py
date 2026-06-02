"""LLM client abstraction for SpecForge.

Supports Anthropic, OpenAI-compatible, and Ollama providers via stdlib
urllib.request — no new runtime dependencies.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable

from pydantic import BaseModel

_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2",
}

_DEFAULT_BASE_URLS: dict[str, str] = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
    "ollama": "http://localhost:11434",
}

_DRAFT_SYSTEM = (
    "You are a requirements engineer writing artifact bodies for a spec-tracking system. "
    "Write a concise, well-structured Markdown body for the artifact described. "
    "Use headers, bullet points, or numbered lists as appropriate for the artifact kind. "
    "Return only the Markdown body — no preamble, no explanation, no code fences."
)


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = ""
    api_key: str = ""
    base_url: str = ""

    def effective_model(self) -> str:
        return self.model or _DEFAULT_MODELS.get(self.provider, "")

    def effective_base_url(self) -> str:
        return self.base_url or _DEFAULT_BASE_URLS.get(self.provider, "")

    def effective_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        env_var = env_map.get(self.provider, "")
        return os.environ.get(env_var, "") if env_var else ""


class LLMError(Exception):
    """Raised when an LLM provider call fails."""


def complete(prompt: str, system: str, config: LLMConfig) -> str:
    """Call the configured LLM provider and return the text response.

    Raises LLMError on HTTP errors or missing API keys.
    """
    provider = config.provider
    if provider == "anthropic":
        return _complete_anthropic(prompt, system, config)
    elif provider in ("openai", "openai-compatible"):
        return _complete_openai(prompt, system, config)
    elif provider == "ollama":
        return _complete_ollama(prompt, system, config)
    else:
        raise LLMError(f"Unknown provider: {provider!r}. Use 'anthropic', 'openai', or 'ollama'.")


def complete_with_fallback(
    prompt: str,
    system: str,
    config: LLMConfig,
    ask_fallback: Callable[[str], bool],
) -> str:
    """Try the primary provider; on LLMError ask whether to fall back to Ollama.

    ask_fallback(error_message) should return True if the user wants Ollama.
    If it returns False, the original LLMError is re-raised.
    """
    try:
        return complete(prompt, system, config)
    except LLMError as exc:
        if ask_fallback(str(exc)):
            ollama_cfg = LLMConfig(
                provider="ollama",
                model=_DEFAULT_MODELS["ollama"],
                base_url=config.effective_base_url() if config.provider == "ollama" else "",
            )
            return complete(prompt, system, ollama_cfg)
        raise


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except Exception as exc:
        raise LLMError(f"Request to {url} failed: {exc}") from exc


def _complete_anthropic(prompt: str, system: str, config: LLMConfig) -> str:
    api_key = config.effective_api_key()
    if not api_key.strip():
        raise LLMError(
            "No API key for Anthropic. Set ANTHROPIC_API_KEY or 'llm.api_key' in .specforge.yaml."
        )
    url = config.effective_base_url().rstrip("/") + "/v1/messages"
    payload = {
        "model": config.effective_model(),
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    data = _post_json(url, payload, headers)
    try:
        return data["content"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected Anthropic response shape: {data}") from exc


def _complete_openai(prompt: str, system: str, config: LLMConfig) -> str:
    api_key = config.effective_api_key()
    if not api_key.strip():
        raise LLMError(
            "No API key for OpenAI. Set OPENAI_API_KEY or 'llm.api_key' in .specforge.yaml."
        )
    url = config.effective_base_url().rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": config.effective_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    data = _post_json(url, payload, headers)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected OpenAI response shape: {data}") from exc


def _complete_ollama(prompt: str, system: str, config: LLMConfig) -> str:
    url = config.effective_base_url().rstrip("/") + "/api/chat"
    payload = {
        "model": config.effective_model(),
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {"Content-Type": "application/json"}
    data = _post_json(url, payload, headers)
    try:
        return data["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected Ollama response shape: {data}") from exc
