"""Independently reconstruct comparisons, including conflicting test interpretations."""

from typing import Literal

from app.clinical.diagnostic_challenger import diagnostic_comparisons
from app.clinical.ports import ClinicalReader, SourceResolver
from app.clinical.result_followup import search_scope
from app.core.provenance import digest
from app.evidence.provenance import anchor_matches
from app.hospital.errors import HospitalError
from app.schemas.investigation import Candidate, Check, SourceRecord, Verification


async def verify_diagnostic_comparison(
    resolver: SourceResolver, patient_id: str, candidate: Candidate
) -> tuple[Verification, str]:
    def result(
        status: Literal["verified", "rejected", "inconclusive"],
        message: str,
        claim: str | None = None,
    ) -> tuple[Verification, str]:
        return Verification(
            status=status,
            classification="SUPPORTED_RECORD_RELATIONSHIP"
            if status == "verified"
            else "REVIEW_REQUIRED",
            checks=[
                Check(
                    type="diagnostic_comparison_reconstruction",
                    status="passed"
                    if status == "verified"
                    else "failed"
                    if status == "rejected"
                    else "inconclusive",
                    message=message,
                )
            ],
        ), claim or "The proposed diagnostic hypothesis comparison is not established."

    relationship = candidate.relationship
    if (
        not relationship
        or not relationship.diagnostic_comparison
        or relationship.conclusion_kind != "record_relationship"
    ):
        return result("inconclusive", "Only a bounded recorded-evidence comparison is supported.")
    comparison = relationship.diagnostic_comparison
    scope = comparison.search
    if not scope.complete or not isinstance(resolver, ClinicalReader):
        return result("inconclusive", "Independent complete counterevidence search is unavailable.")
    rows: list[SourceRecord] = []
    try:
        for kind in ("diagnostic_report", "document", "encounter", "referral"):
            page, total = await resolver.records(kind, patient_id, {"limit": 100, "offset": 0})
            if len(page) != total or total > (20 if kind == "document" else 100):
                return result("inconclusive", "Independent diagnostic source search is truncated.")
            for listed in page:
                original = await resolver.resolve(patient_id, listed.source)
                if (
                    original != listed
                    or original.representation != "source"
                    or (
                        original.data.get("patient_id") != patient_id
                        or original.data.get("id") != original.source.id
                        or digest(original.data) != original.source_hash
                    )
                ):
                    return result(
                        "rejected",
                        "Original identity, patient, representation or fingerprint failed.",
                    )
                rows.append(original)
    except HospitalError:
        return result("inconclusive", "An original diagnostic source is unavailable.")
    if len(rows) > 120 or search_scope(rows, True) != scope:
        return result("rejected", "Accessible source scope changed or omitted counterevidence.")
    if any(
        r.source.type == "document"
        and (
            not isinstance(r.data.get("text_content"), str)
            or not r.data["text_content"].strip()
            or len(r.data["text_content"]) > 2000
        )
        for r in rows
    ):
        return result(
            "inconclusive", "Unparsed document text prevents a complete interpretation comparison."
        )
    by_source = {(r.source.type, r.source.id): r for r in rows}
    for citation in candidate.anchors:
        row = by_source.get((citation.source.type, citation.source.id))
        if not row or not anchor_matches(row, citation):
            return result("rejected", "A source anchor failed independent validation.")
    canonical = next(
        (
            c
            for c in diagnostic_comparisons(rows, scope)
            if c.relationship == relationship
            and c.anchors == candidate.anchors
            and c.claim_kind == candidate.claim_kind
        ),
        None,
    )
    if not canonical:
        return result(
            "rejected",
            "Working assessment, test context, counterevidence or comparison cannot be reproduced.",
        )
    return result(
        "verified",
        "Original evidence relationship independently reconstructed; "
        "clinical verdict remains provisional.",
        canonical.claim,
    )
