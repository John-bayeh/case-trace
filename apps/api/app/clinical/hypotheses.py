"""Proposition-relevant evidence assessment; citations alone do not support explanations."""

from app.clinical.claims import ClinicalClaim
from app.clinical.extraction import extract_claims
from app.schemas.investigation import Candidate, Hypothesis, SourceRecord


def assess_hypotheses(candidates: list[Candidate]) -> list[Hypothesis]:
    assessments = []
    for candidate in candidates:
        if candidate.type != "timeline_contradiction":
            continue
        relevant: list[ClinicalClaim] = []
        for anchor in candidate.anchors:
            if anchor.field not in {"text_content", "description"}:
                continue
            row = SourceRecord(
                source=anchor.source,
                source_version=anchor.source_version,
                source_hash=anchor.source_hash,
                data={anchor.field: anchor.expected, "encounter_id": anchor.encounter_id},
            )
            relevant.extend(
                claim.model_copy(update={"anchor": anchor})
                for claim in extract_claims(row)
                if anchor.quote is None or (claim.anchor.quote or "") in anchor.quote
            )
        onsets = [c for c in relevant if c.assertion == "onset"]
        for onset in onsets[:1]:
            supports = [
                c.anchor
                for c in relevant
                if c.concept == onset.concept and c.episode_scope in {"new", "recurrent"}
            ]
            weakens = [onset.anchor] if onset.episode_scope == "first" else []
            assessments.append(
                Hypothesis(
                    explanation="Different symptom episodes may explain the recorded chronology.",
                    supports=supports[:20],
                    weakens=weakens,
                    missing_evidence=[
                        "Explicit episode linkage and intervening resolution history.",
                        "Clarification of the recorded first-onset history.",
                    ],
                    verdict="inconclusive",
                    limitations=[
                        "A first-onset assertion challenges separate episodes "
                        "but cannot establish clinical truth."
                    ],
                    alternatives=[
                        "Retrospective reporting error remains untested "
                        "without a correction or clarification."
                    ],
                )
            )
    return assessments[:10]
