"""Independent source reconstruction for typed relationship candidates."""

from app.clinical.extraction import extract_claims
from app.clinical.medications import medication_assertions, medication_relationships
from app.clinical.ports import SourceResolver
from app.clinical.relationship_synthesis import synthesize_relationships
from app.clinical.rules import instant
from app.core.provenance import digest
from app.evidence.provenance import anchor_matches
from app.hospital.errors import HospitalError
from app.schemas.investigation import Candidate, Check, SourceRecord, Verification


async def verify_relationship(
    resolver: SourceResolver,
    patient_id: str,
    candidate: Candidate,
) -> tuple[Verification, str]:
    checks: list[Check] = []

    def result(
        status: str, check: str, message: str, claim: str | None = None
    ) -> tuple[Verification, str]:
        checks.append(
            Check(
                type=check,
                status="passed"
                if status == "verified"
                else "failed"
                if status == "rejected"
                else "inconclusive",
                message=message,
            )
        )
        return Verification(
            status=status,  # type: ignore[arg-type]
            checks=checks,
            classification="SUPPORTED_RECORD_RELATIONSHIP"
            if status == "verified"
            else "RELATIONSHIP_REJECTED"
            if status == "rejected"
            else "REVIEW_REQUIRED",
        ), claim or "The proposed clinical relationship is not established by verified evidence."

    evidence = candidate.relationship
    if (
        not evidence
        or candidate.rule != "clinical_relationship"
        or candidate.type != "clinical_relationship"
    ):
        return result(
            "rejected",
            "relationship_schema",
            "Typed relationship rule and evidence are required together.",
        )
    if evidence.conclusion_kind in {"ingestion", "causality", "diagnosis"}:
        return result(
            "rejected",
            "conclusion_scope",
            "Definitive exposure, causal and diagnostic conclusions are unsupported.",
        )
    if evidence.relationship_type == "result_followup" and evidence.result_workflow is not None:
        from app.evidence.result_followup import verify_result_followup

        return await verify_result_followup(resolver, patient_id, candidate)
    if (
        evidence.relationship_type == "hypothesis_challenge"
        and evidence.diagnostic_comparison is not None
    ):
        from app.evidence.diagnostic_challenger import verify_diagnostic_comparison

        return await verify_diagnostic_comparison(resolver, patient_id, candidate)
    ids = [a.id for a in evidence.assertions]
    identities = [a.anchor.model_dump_json() for a in evidence.assertions]
    if len(set(ids)) != len(ids) or len(set(identities)) != len(identities):
        return result(
            "rejected",
            "assertion_uniqueness",
            "Repeated assertions cannot supply independent evidence.",
        )
    anchors = [
        (a.source.type, a.source.id, a.field, a.char_start, a.char_end) for a in candidate.anchors
    ]
    if len(set(anchors)) != len(anchors):
        return result(
            "rejected",
            "evidence_completeness",
            "Duplicate source anchors are not independent evidence.",
        )
    records: dict[tuple[str, str], SourceRecord] = {}
    for anchor in candidate.anchors:
        key = (anchor.source.type, anchor.source.id)
        try:
            if key not in records:
                records[key] = await resolver.resolve(patient_id, anchor.source)
            row = records[key]
            valid = (
                row.data.get("patient_id") == patient_id
                and row.data.get("id") == anchor.source.id
                and digest(row.data) == row.source_hash
                and anchor_matches(row, anchor)
            )
        except HospitalError:
            valid = False
        checks.append(
            Check(
                type="source_existence",
                status="passed" if valid else "failed",
                message="Independent patient-scoped source, version, hash and anchor check.",
            )
        )
    if any(c.status == "failed" for c in checks):
        return result(
            "rejected",
            "source_integrity",
            "A relationship source is unavailable, foreign or changed.",
        )
    for assertion in evidence.assertions:
        original = records.get((assertion.anchor.source.type, assertion.anchor.source.id))
        reproduced = (
            medication_assertions(original, list(records.values()))
            if original and assertion.id.startswith("MC-")
            else extract_claims(original)
            if original
            else []
        )
        if not original or not any(a == assertion for a in reproduced):
            return result(
                "rejected",
                "assertion_reconstruction",
                "A factual assertion cannot be reproduced from the original record.",
            )
        role = "contradicts" if assertion.id in evidence.contradicting_assertion_ids else "supports"
        required = assertion.anchor.model_copy(update={"relationship": role})
        if required not in candidate.anchors:
            return result(
                "rejected",
                "evidence_completeness",
                "A constituent assertion's exact evidence role/anchor is missing.",
            )
    checks.append(
        Check(
            type="assertion_reconstruction",
            status="passed",
            message="All constituent assertions reproduced from hospital originals.",
        )
    )
    by_id = {a.id: a for a in evidence.assertions}
    for ordering in evidence.temporal_ordering:
        earlier, later = by_id[ordering.earlier_assertion_id], by_id[ordering.later_assertion_id]
        left = records[(earlier.anchor.source.type, earlier.anchor.source.id)]
        right = records[(later.anchor.source.type, later.anchor.source.id)]
        at, bt = (
            instant(left.data.get(ordering.earlier_field)),
            instant(right.data.get(ordering.later_field)),
        )
        if not at or not bt:
            return result(
                "inconclusive",
                "temporal_ordering",
                "Comparable aware instants are unavailable; no ordering is established.",
            )
        if at >= bt:
            return result(
                "rejected", "temporal_ordering", "The proposed source chronology is false."
            )
    if evidence.conclusion_kind == "interpretation" or evidence.relationship_type not in {
        "recorded_state_difference",
        "documented_assertion_conflict",
        "medication_reconciliation",
    }:
        return result(
            "inconclusive",
            "relationship_semantics",
            "Clinical interpretation requires a specific rule or qualified review.",
        )
    supplied = [a.model_dump() for a in candidate.anchors]
    regenerated = next(
        (
            c
            for c in (
                medication_relationships(list(records.values()))
                if evidence.relationship_type == "medication_reconciliation"
                else synthesize_relationships(list(records.values()))
            )
            if c.relationship == evidence
            and c.claim_kind == candidate.claim_kind
            and len(c.anchors) == len(supplied)
            and all(a.model_dump() in supplied for a in c.anchors)
        ),
        None,
    )
    if not regenerated:
        return result(
            "rejected",
            "relationship_constraints",
            "The relationship, decisive evidence or temporal constraints cannot be reproduced.",
        )
    return result(
        "verified",
        "relationship_constraints",
        "Source-level relationship independently reproduced; clinical meaning remains limited.",
        regenerated.claim,
    )
