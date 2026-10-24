"""Provisional comparisons; working diagnoses are documented opinions, not truth."""

from typing import Literal

from pydantic import Field

from app.clinical.result_models import ResultSearchScope
from app.hospital.schemas import ClinicalModel
from app.schemas.provenance import Anchor

ComparisonVerdict = Literal["reconsideration_question", "not_challenged", "inconclusive"]
DiagnosticCertainty = Literal["provisional", "suspected", "documented_assessment_unknown_certainty"]


class DiagnosticEvidence(ClinicalModel):
    attribution: Literal["explicit", "nonspecific_context"] = "explicit"
    role: Literal[
        "working_assessment",
        "symptom_context",
        "test_order",
        "objective_interpretation",
        "reassessment",
        "referral",
        "supporting_interpretation",
        "counterinterpretation",
    ]
    anchor: Anchor
    timestamps: dict[str, str | None] = Field(default_factory=dict)


class DiagnosticComparison(ClinicalModel):
    hypothesis: str = Field(max_length=200)
    certainty: DiagnosticCertainty
    scope: Literal["sufficiency_of_working_explanation"] = "sufficiency_of_working_explanation"
    evidence: list[DiagnosticEvidence] = Field(min_length=2, max_length=20)
    supporting_evidence: list[Anchor] = Field(default_factory=list, max_length=10)
    weakening_evidence: list[Anchor] = Field(default_factory=list, max_length=10)
    contradictory_evidence: list[Anchor] = Field(default_factory=list, max_length=10)
    missing_evidence: list[str] = Field(min_length=1, max_length=10)
    alternatives: list[str] = Field(min_length=1, max_length=10)
    question: str = Field(max_length=1000)
    provisional_verdict: ComparisonVerdict
    search: ResultSearchScope
