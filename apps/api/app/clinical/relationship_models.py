"""Bounded relationship evidence, composed from the existing factual assertion model."""

from typing import Literal

from pydantic import Field, model_validator

from app.clinical.claims import ClinicalClaim
from app.clinical.diagnostic_models import DiagnosticComparison
from app.clinical.result_models import ResultWorkflow
from app.hospital.schemas import ClinicalModel


class TemporalOrdering(ClinicalModel):
    earlier_assertion_id: str
    earlier_field: str
    later_assertion_id: str
    later_field: str
    relation: Literal["before"] = "before"


class RelationshipEvidence(ClinicalModel):
    schema_version: Literal["1.0"] = "1.0"
    result_workflow: ResultWorkflow | None = None
    diagnostic_comparison: DiagnosticComparison | None = None
    relationship_type: Literal[
        "recorded_state_difference",
        "documented_assertion_conflict",
        "medication_reconciliation",
        "result_followup",
        "hypothesis_challenge",
        "longitudinal_followup",
    ]
    assertions: list[ClinicalClaim] = Field(min_length=2, max_length=8)
    supporting_assertion_ids: list[str] = Field(min_length=1, max_length=8)
    contradicting_assertion_ids: list[str] = Field(default_factory=list, max_length=8)
    temporal_ordering: list[TemporalOrdering] = Field(default_factory=list, max_length=8)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=10)
    conclusion_kind: Literal[
        "record_relationship", "interpretation", "ingestion", "causality", "diagnosis"
    ] = "record_relationship"

    @model_validator(mode="after")
    def references(self) -> "RelationshipEvidence":
        ids = {a.id for a in self.assertions}
        roles = self.supporting_assertion_ids + self.contradicting_assertion_ids
        # Duplicate factual assertions are rejected by verification, not silently merged.
        if set(roles) != ids or len(set(roles)) != len(roles):
            raise ValueError("Every assertion must have exactly one evidence role")
        if any(
            t.earlier_assertion_id not in ids or t.later_assertion_id not in ids
            for t in self.temporal_ordering
        ):
            raise ValueError("Temporal constraints must reference constituent assertions")
        return self
