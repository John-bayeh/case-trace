"""Strict Responses wire schema; arbitrary clinical values travel as validated JSON strings."""

import json
from typing import Literal

from app.hospital.schemas import ClinicalModel
from app.schemas.investigation import AgentResult, Candidate
from app.schemas.provenance import Anchor, SourceRef


class ProposalAnchor(ClinicalModel):
    source: SourceRef
    source_version: int
    source_hash: str
    encounter_id: str | None
    field: str
    expected_json: str
    quote: str | None
    relationship: Literal["supports", "contradicts", "contextualizes", "derived_from"]


class Proposal(ClinicalModel):
    type: Literal[
        "timeline_contradiction",
        "laboratory_change",
        "medication_change",
        "documentation_delay",
        "missing_evidence",
        "clinical_relationship",
    ]
    title: str
    claim: str
    claim_kind: Literal["observation", "chronology", "interpretation", "hypothesis"]
    rule: Literal[
        "field_observation",
        "lab_change",
        "review_before_result",
        "onset_conflict",
        "interpretation",
    ]
    anchors: list[ProposalAnchor]
    alternatives: list[str]
    limitations: list[str]


class Proposals(ClinicalModel):
    candidates: list[Proposal]
    limitations: list[str]

    def validated(self) -> AgentResult:
        return AgentResult(
            candidates=[
                Candidate(
                    **p.model_dump(exclude={"anchors"}),
                    anchors=[
                        Anchor(
                            **a.model_dump(exclude={"expected_json"}),
                            expected=json.loads(a.expected_json),
                        )
                        for a in p.anchors
                    ],
                )
                for p in self.candidates
            ],
            limitations=self.limitations,
        )
