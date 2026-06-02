from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArtifactKind(StrEnum):
    IDEA = "idea"
    CANDIDATE = "candidate"
    REQUIREMENT = "requirement"
    DECISION = "decision"
    ASSUMPTION = "assumption"
    CONSTRAINT = "constraint"
    CHANGE_ORDER = "change_order"
    TASK = "task"
    TEST = "test"
    VERIFICATION = "verification"
    REFERENCE = "reference"
    CONVERSATION = "conversation"
    WORK_LOG = "work_log"
    CHANGELOG = "changelog"
    TEST_LOG = "test_log"
    VERIFICATION_LOG = "verification_log"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    ARCHIVED = "archived"


PREFIX_BY_KIND: dict[ArtifactKind, str] = {
    ArtifactKind.IDEA: "IDEA",
    ArtifactKind.CANDIDATE: "CAND",
    ArtifactKind.REQUIREMENT: "REQ",
    ArtifactKind.DECISION: "DEC",
    ArtifactKind.ASSUMPTION: "ASM",
    ArtifactKind.CONSTRAINT: "CON",
    ArtifactKind.CHANGE_ORDER: "CO",
    ArtifactKind.TASK: "TASK",
    ArtifactKind.TEST: "TEST",
    ArtifactKind.VERIFICATION: "VER",
    ArtifactKind.REFERENCE: "REF",
    ArtifactKind.CONVERSATION: "CONV",
    ArtifactKind.WORK_LOG: "WORK",
    ArtifactKind.CHANGELOG: "CHG",
    ArtifactKind.TEST_LOG: "TLOG",
    ArtifactKind.VERIFICATION_LOG: "VLOG",
}


class Artifact(BaseModel):
    id: str
    kind: ArtifactKind
    title: str
    status: ArtifactStatus = ArtifactStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    related_requirements: list[str] = Field(default_factory=list)
    related_decisions: list[str] = Field(default_factory=list)
    related_assumptions: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    verified_by: list[str] = Field(default_factory=list)
    implements: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    body: str = ""
    path: Path | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def id_must_be_upper(cls, value: str) -> str:
        if value != value.upper():
            raise ValueError("artifact IDs must be uppercase")
        return value

    def to_frontmatter(self) -> dict[str, Any]:
        data = self.model_dump(exclude={"body", "path"})
        data["kind"] = self.kind.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data
