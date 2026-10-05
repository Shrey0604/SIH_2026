from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtractedEvent(BaseModel):
    """Strict boundary between model output and the NWIS event store."""

    model_config = ConfigDict(extra="forbid")

    hazard_type: Literal["MUD_LOSS", "STUCK_PIPE", "KICK"]
    formation: str | None = Field(default=None, min_length=1, max_length=80)
    start_md_m: float = Field(ge=0, le=20_000)
    end_md_m: float | None = Field(default=None, ge=0, le=20_000)
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    description: str = Field(min_length=12, max_length=1_500)
    historical_response: str | None = Field(default=None, max_length=1_500)
    page_number: int = Field(ge=1)
    evidence_text: str = Field(min_length=12, max_length=2_500)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_depth_interval(self) -> "ExtractedEvent":
        if self.end_md_m is not None and self.end_md_m < self.start_md_m:
            raise ValueError("end_md_m cannot be shallower than start_md_m")
        return self


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[ExtractedEvent] = Field(default_factory=list, max_length=30)


class GroundedAnswer(BaseModel):
    """Structured synthesis contract used by the future Phase 5 backend."""

    model_config = ConfigDict(extra="forbid")

    answer_markdown: str = Field(min_length=1, max_length=8_000)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    insufficient_evidence: bool
