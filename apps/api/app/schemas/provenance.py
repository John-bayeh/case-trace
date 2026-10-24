"""Neutral source identity and exact citation schemas; public re-exports stay compatible."""

from typing import Any, Literal

from pydantic import Field, model_validator

from app.hospital.schemas import ClinicalModel, Identifier

SourceType = Literal[
    "patient",
    "encounter",
    "clinical_event",
    "observation",
    "medication",
    "document",
    "imaging_study",
    "imaging_asset",
    "referral",
    "diagnostic_report",
    "diagnosis",
    "symptom",
]


class SourceRef(ClinicalModel):
    type: SourceType
    id: Identifier


class Anchor(ClinicalModel):
    source: SourceRef
    source_version: int = Field(ge=1)
    source_hash: str = Field(min_length=64, max_length=64)
    encounter_id: str | None = None
    field: str = Field(min_length=1, max_length=100)
    expected: Any
    quote: str | None = Field(default=None, max_length=2000)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=1)
    relationship: Literal["supports", "contradicts", "contextualizes", "derived_from"] = "supports"

    @model_validator(mode="after")
    def paired_offsets(self) -> "Anchor":
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("Source offsets must be paired")
        if self.char_start is not None and (
            self.quote is None or self.char_end is None or self.char_end <= self.char_start
        ):
            raise ValueError("Source offsets require a nonempty exact quote")
        return self
