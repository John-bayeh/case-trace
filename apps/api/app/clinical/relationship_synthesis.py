"""Pure bounded relationship assembly over original tool-returned records."""

from itertools import combinations

from app.clinical.claims import ClinicalClaim
from app.clinical.comparison import compare_claims
from app.clinical.extraction import extract_claims
from app.clinical.relationship_models import RelationshipEvidence, TemporalOrdering
from app.clinical.rules import anchor, instant
from app.schemas.investigation import Anchor, Candidate, SourceRecord

MAX_RELATIONSHIPS = 8
MAX_RELATIONSHIP_PAIRS = 4096
RELATIONSHIP_LIMITATIONS = [
    "Relationships concern recorded assertions, not established clinical truth.",
    "Order/status records do not prove ingestion, administration, causality or diagnosis.",
    "Unretrieved sources and undocumented care remain unknown.",
]
RELATIONSHIP_ALTERNATIVES = [
    "Different effective times, planned changes or documentation updates may explain the records."
]


def relationship_candidate(
    relationship_type: str,
    assertions: list[ClinicalClaim],
    rows: list[SourceRecord],
    supporting_ids: list[str],
    contradicting_ids: list[str],
    ordering: list[TemporalOrdering],
    claim: str,
) -> Candidate:
    evidence = RelationshipEvidence(
        relationship_type=relationship_type,  # type: ignore[arg-type]
        assertions=assertions,
        supporting_assertion_ids=supporting_ids,
        contradicting_assertion_ids=contradicting_ids,
        temporal_ordering=ordering,
        unresolved_questions=["What explains these documented assertions?"],
    )
    citations: list[Anchor] = []
    for assertion, row in zip(assertions, rows, strict=True):
        role = "contradicts" if assertion.id in contradicting_ids else "supports"
        citations.append(assertion.anchor.model_copy(update={"relationship": role}))
        identity_fields = (
            ["medication_name", "generic_name"]
            if row.source.type == "medication"
            else ["reason", "referred_department"]
            if row.source.type == "referral"
            else []
        )
        fields = [*identity_fields, assertion.event_time_field, assertion.documentation_time_field]
        for field in fields:
            if field and row.data.get(field) is not None:
                citations.append(anchor(row, field))
    unique = {a.model_dump_json(): a for a in citations}
    return Candidate(
        type="clinical_relationship",
        title="Recorded clinical relationship",
        claim=claim,
        claim_kind="observation",
        rule="clinical_relationship",
        anchors=list(unique.values()),
        relationship=evidence,
        alternatives=RELATIONSHIP_ALTERNATIVES,
        limitations=RELATIONSHIP_LIMITATIONS,
    )


def compare_assertions(
    a: ClinicalClaim,
    b: ClinicalClaim,
    first: SourceRecord,
    second: SourceRecord,
) -> Candidate | None:
    """Only two implemented source-level propositions; broader meaning stays reviewable."""
    if (
        not a.patient_id
        or a.patient_id != b.patient_id
        or a.concept != b.concept
        or a.anchor.source == b.anchor.source
        or not a.anchor.encounter_id
        or not b.anchor.encounter_id
        or a.anchor.encounter_id == b.anchor.encounter_id
        or a.subject != "patient"
        or b.subject != "patient"
        or a.certainty != "asserted"
        or b.certainty != "asserted"
    ):
        return None
    if (
        a.assertion == b.assertion
        and a.assertion in {"medication_status", "followup_status"}
        and a.value != b.value
        and a.polarity == b.polarity == "positive"
        and first.source.type == second.source.type
    ):
        fields = (
            ["medication_name", "generic_name"]
            if first.source.type == "medication"
            else ["reason", "referred_department"]
        )
        if any(first.data.get(f) != second.data.get(f) for f in fields):
            return None
        at, bt = instant(first.data.get("ordered_at")), instant(second.data.get("ordered_at"))
        if not at or not bt or at == bt:
            return None
        if at > bt:
            a, b, first, second = b, a, second, first
        ordering = [
            TemporalOrdering(
                earlier_assertion_id=a.id,
                earlier_field="ordered_at",
                later_assertion_id=b.id,
                later_field="ordered_at",
            )
        ]
        return relationship_candidate(
            "recorded_state_difference",
            [a, b],
            [first, second],
            [a.id, b.id],
            [],
            ordering,
            f"{a.anchor.source.id} and {b.anchor.source.id} record different {a.concept} "
            f"states ({a.value}; {b.value}), with the former order preceding the latter. "
            "This does not establish a contradiction, actual exposure or the effective time "
            "of a status update.",
        )
    # Established narrow chronology semantics, independently reproduced by the verifier.
    for onset, prior, onset_row, prior_row in [(a, b, first, second), (b, a, second, first)]:
        if compare_claims(onset, prior, prior_row).status != "documented_conflict":
            continue
        if not prior.event_time_field or not onset.event_time_field:
            continue
        return relationship_candidate(
            "documented_assertion_conflict",
            [onset, prior],
            [onset_row, prior_row],
            [onset.id],
            [prior.id],
            [
                TemporalOrdering(
                    earlier_assertion_id=prior.id,
                    earlier_field=prior.event_time_field,
                    later_assertion_id=onset.id,
                    later_field=onset.event_time_field,
                )
            ],
            f"{onset.anchor.source.id}'s first-onset assertion conflicts with "
            f"{prior.anchor.source.id}'s earlier contemporaneous {onset.concept} assertion. "
            "The true onset, explanation and clinical cause remain unresolved.",
        )
    return None


def synthesize_relationships(
    records: list[SourceRecord],
    *,
    states_only: bool = False,
) -> list[Candidate]:
    rows = sorted(
        [
            r
            for r in records[:100]
            if r.representation == "source"
            and (not states_only or r.source.type in {"medication", "referral"})
        ],
        key=lambda r: (r.source.type not in {"medication", "referral"}, r.source.type, r.source.id),
    )
    assertions = [(a, row) for row in rows for a in extract_claims(row)]
    results = []
    seen = set()
    for index, ((a, first), (b, second)) in enumerate(combinations(assertions, 2)):
        if index >= MAX_RELATIONSHIP_PAIRS:
            break
        candidate = compare_assertions(a, b, first, second)
        if not candidate:
            continue
        key = candidate.model_dump_json()
        if key not in seen:
            seen.add(key)
            results.append(candidate)
        if len(results) == MAX_RELATIONSHIPS:
            break
    return results
