"""Bounded longitudinal evidence; raw values and named times remain source specific."""

from typing import Any, Literal

from pydantic import Field

from app.hospital.schemas import ClinicalModel
from app.schemas.provenance import Anchor, SourceRef


class SeriesSource(ClinicalModel):
    source: SourceRef
    version: int
    hash: str


class Measurement(ClinicalModel):
    value: Anchor
    context: dict[str, Any]


class LongitudinalEvidence(ClinicalModel):
    group: str
    measurements: list[Measurement] = Field(min_length=2, max_length=40)
    search: list[SeriesSource] = Field(max_length=240)
    search_complete: bool
    followup: list[Anchor] = Field(max_length=20)
    followup_state: Literal["documented", "not_documented", "unknown"]
    question: str
    stop_reason: Literal["evidence_sufficient", "evidence_unavailable", "budget_exhausted"]
