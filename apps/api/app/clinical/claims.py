"""Internal source assertions, distinct from verified findings and diagnoses."""

from datetime import date
from typing import Literal

from pydantic import Field

from app.hospital.schemas import ClinicalModel
from app.schemas.provenance import Anchor


class ClaimTime(ClinicalModel):
    start: date | None = None
    end: date | None = None
    precision: Literal["day", "month", "approximate", "unknown"] = "unknown"
    basis: Literal["explicit", "relative", "encounter", "historical", "unknown"] = "unknown"
    reference: str | None = None
    original: str | None = None


class ClinicalClaim(ClinicalModel):
    id: str
    patient_id: str | None = None
    anchor: Anchor
    concept: str
    original_concept: str
    qualifiers: list[str] = Field(default_factory=list)
    assertion: Literal[
        "onset",
        "presence",
        "absence",
        "recurrence",
        "resolution",
        "worsening",
        "impression",
        "observation",
        "medication_status",
        "followup_status",
    ]
    subject: Literal["patient", "family", "unknown"] = "patient"
    attribution: Literal["patient_report", "clinician_record", "unknown"] = "clinician_record"
    polarity: Literal["positive", "negative"] = "positive"
    certainty: Literal["asserted", "uncertain", "hypothetical"] = "asserted"
    temporality: Literal["current", "historical", "unknown"] = "unknown"
    time: ClaimTime = Field(default_factory=ClaimTime)
    episode_id: str | None = None
    episode_scope: Literal["first", "recurrent", "new", "unspecified"] = "unspecified"
    section: str | None = None
    value: float | str | None = None
    unit: str | None = None
    recorded_status: str | None = None
    timestamps: dict[str, str | None] = Field(default_factory=dict)
    origin: Literal[
        "order",
        "observation",
        "patient_report",
        "clinician_record",
        "clinician_interpretation",
        "copied_list",
        "administration",
        "unknown",
    ] = "unknown"
    source_status: str | None = None
    event_time_field: str | None = None
    documentation_time_field: str | None = None
    extraction_method: Literal["rules_v1", "model_proposal"] = "rules_v1"
    limitations: list[str] = Field(default_factory=list)


class ClaimComparison(ClinicalModel):
    claim_a: ClinicalClaim
    claim_b: ClinicalClaim
    relationship: Literal["onset_chronology", "polarity", "unresolved"]
    status: Literal[
        "documented_conflict",
        "potential_conflict",
        "different_episodes",
        "documentation_delay",
        "compatible",
        "ambiguous",
        "insufficient_evidence",
    ]
    reason: str
    assumptions: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
