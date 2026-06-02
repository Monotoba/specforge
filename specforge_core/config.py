from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

from .llm import LLMConfig
from .webhooks import WebhookEntry

CONFIG_FILENAME = ".specforge.yaml"

_COMMENTED_DEFAULT = """\
# SpecForge project configuration
# All settings are optional — omit any key to use the default.

# Human-readable project name (used in reports and status dashboard)
project_name: ""

# Automatically commit every artifact write to git (equivalent to passing --git each time)
git_commit: false

# LLM provider for 'specforge draft' (anthropic | openai | ollama)
# llm:
#   provider: anthropic
#   model: claude-sonnet-4-6
#   api_key: ""        # falls back to ANTHROPIC_API_KEY env var
#   base_url: ""       # override endpoint; Ollama default: http://localhost:11434

# Webhooks: POST to these URLs on artifact events
# webhooks:
#   - url: https://example.com/hook
#     events: [artifact.created, artifact.promoted]
#     secret: "optional-hmac-secret"
"""


class ProjectConfig(BaseModel):
    project_name: str = ""
    git_commit: bool = False
    llm: LLMConfig = LLMConfig()
    webhooks: list[WebhookEntry] = []

    @field_validator("project_name", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v: Any) -> str:
        return "" if v is None else str(v)


def load_config(root: Path) -> ProjectConfig:
    path = root / CONFIG_FILENAME
    if not path.exists():
        return ProjectConfig()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return ProjectConfig()
        return ProjectConfig(**{k: v for k, v in data.items() if k in ProjectConfig.model_fields})
    except Exception:
        return ProjectConfig()


def save_config(root: Path, config: ProjectConfig) -> None:
    path = root / CONFIG_FILENAME
    path.write_text(
        yaml.safe_dump(config.model_dump(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def write_default_config(root: Path) -> None:
    """Write a commented default config file; does nothing if one already exists."""
    path = root / CONFIG_FILENAME
    if not path.exists():
        path.write_text(_COMMENTED_DEFAULT, encoding="utf-8")
