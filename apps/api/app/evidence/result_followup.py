"""Independent accessible-search reconstruction, including omitted counterevidence."""

from typing import Literal

from app.clinical.ports import ClinicalReader, SourceResolver
from app.clinical.result_followup import result_relationships, search_scope
from app.core.provenance import digest
from app.evidence.provenance import anchor_matches
from app.hospital.errors import HospitalError
from app.schemas.investigation import Candidate, Check, SourceRecord, Verification


async def verify_result_followup(
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
                    type="result_workflow_reconstruction",
                    status="passed"
                    if status == "verified"
                    else "failed"
                    if status == "rejected"
                    else "inconclusive",
                    message=message,
                )
            ],
        ), claim or "The documented result-to-follow-up relationship is not established."

    evidence = candidate.relationship
    if (
        not evidence
        or not evidence.result_workflow
        or evidence.conclusion_kind != "record_relationship"
    ):
        return result(
            "inconclusive", "A bounded record relationship with search scope is required."
        )
    scope = evidence.result_workflow.search
    if not scope.complete or not isinstance(resolver, ClinicalReader):
        return result(
            "inconclusive",
            "Complete independent clinical search is unavailable; absent care cannot be inferred.",
        )
    if scope.categories != ["diagnostic_report", "document", "encounter", "referral"]:
        return result("rejected", "The required search categories were changed.")
    rows: list[SourceRecord] = []
    try:
        for kind in ("diagnostic_report", "document", "encounter", "referral"):
            page, total = await resolver.records(kind, patient_id, {"limit": 100, "offset": 0})
            if len(page) != total or total > (scope.document_limit if kind == "document" else 100):
                return result("inconclusive", "Independent accessible-record search is truncated.")
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
                        "Search result ownership, identity or source fingerprint failed.",
                    )
                rows.append(original)
    except HospitalError:
        return result("inconclusive", "An independently searched original is unavailable.")
    if len(rows) > 120 or search_scope(rows, True) != scope:
        return result(
            "rejected", "The searched source manifest changed or omitted accessible records."
        )
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
            "inconclusive",
            "A searched document has unavailable or over-limit text; completion remains unknown.",
        )
    by_source = {(r.source.type, r.source.id): r for r in rows}
    for citation in candidate.anchors:
        row = by_source.get((citation.source.type, citation.source.id))
        if not row or not anchor_matches(row, citation):
            return result("rejected", "A decisive original anchor failed independent verification.")
    regenerated = next(
        (
            c
            for c in result_relationships(rows, scope)
            if c.relationship == evidence
            and c.anchors == candidate.anchors
            and c.claim_kind == candidate.claim_kind
        ),
        None,
    )
    if not regenerated:
        return result(
            "rejected",
            "Lifecycle, recommendation, source roles or later counterevidence "
            "cannot be reproduced.",
        )
    return result(
        "verified",
        "Result date, recommendation, lifecycle and all searched "
        "originals independently reconstructed; undocumented care remains unknown.",
        regenerated.claim,
    )
