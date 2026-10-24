"""Independent bounded longitudinal search and original-source reconstruction."""

from typing import Literal

from app.clinical.longitudinal import SEARCH_LIMIT, groups, manifest
from app.clinical.longitudinal import candidate as rebuild
from app.clinical.ports import ClinicalReader, SourceResolver
from app.core.provenance import digest
from app.evidence.provenance import anchor_matches
from app.hospital.errors import HospitalError
from app.schemas.investigation import Candidate, Check, SourceRecord, Verification


async def verify_longitudinal(
    resolver: SourceResolver, patient_id: str, proposed: Candidate
) -> tuple[Verification, str]:
    def result(
        status: Literal["verified", "rejected", "inconclusive"],
        message: str,
        claim: str = "The longitudinal follow-up relationship remains unverified.",
    ) -> tuple[Verification, str]:
        return Verification(
            status=status,
            classification="SUPPORTED_RECORD_RELATIONSHIP"
            if status == "verified"
            else "INSUFFICIENT_EVIDENCE",
            checks=[
                Check(
                    type="longitudinal_reconstruction",
                    status="passed"
                    if status == "verified"
                    else "failed"
                    if status == "rejected"
                    else "inconclusive",
                    message=message,
                )
            ],
        ), claim

    evidence = proposed.longitudinal
    if (
        not evidence
        or proposed.rule != "longitudinal_followup"
        or proposed.type != "clinical_relationship"
        or proposed.claim_kind != "observation"
        or proposed.relationship is not None
    ):
        return result("rejected", "A bounded observation-only longitudinal envelope is required.")
    rows: list[SourceRecord] = []
    try:
        if evidence.search_complete:
            if not isinstance(resolver, ClinicalReader):
                return result("inconclusive", "Independent accessible search is unavailable.")
            for kind in ("observation", "document", "encounter", "referral"):
                offset = 0
                while True:
                    page, total = await resolver.records(
                        kind, patient_id, {"limit": 100, "offset": offset}
                    )
                    if total + len(rows) - offset > SEARCH_LIMIT:
                        return result("inconclusive", "Independent search budget exhausted.")
                    rows.extend(page)
                    offset += len(page)
                    if offset >= total:
                        break
                    if not page:
                        return result("inconclusive", "Independent pagination stalled.")
            if manifest(rows) != evidence.search:
                return result(
                    "rejected", "Accessible source manifest changed or omitted counterevidence."
                )
        else:
            # Partial searches can establish only what the retained originals say.
            rows = [await resolver.resolve(patient_id, s.source) for s in evidence.search]
        originals = []
        for row in rows:
            original = await resolver.resolve(patient_id, row.source)
            if (
                original != row
                or original.representation != "source"
                or original.data.get("patient_id") != patient_id
                or digest(original.data) != original.source_hash
            ):
                return result("rejected", "Original identity, ownership or fingerprint failed.")
            originals.append(original)
    except HospitalError:
        return result("inconclusive", "A searched source is unavailable.")
    if manifest(originals) != evidence.search:
        return result("rejected", "Source versions or fingerprints changed.")
    by_source = {(r.source.type, r.source.id): r for r in originals}
    for citation in proposed.anchors + evidence.followup + [m.value for m in evidence.measurements]:
        cited_row = by_source.get((citation.source.type, citation.source.id))
        if cited_row is None or not anchor_matches(cited_row, citation):
            return result("rejected", "A decisive measurement or follow-up anchor failed.")
    values = groups(originals).get(evidence.group)
    if not values:
        return result("rejected", "Compatible repeated abnormalities cannot be reconstructed.")
    canonical = rebuild(evidence.group, values, originals, evidence.search_complete)
    if canonical.longitudinal != evidence or canonical.anchors != proposed.anchors:
        return result(
            "rejected", "Measurement context, intervals or follow-up interpretation changed."
        )
    return result(
        "verified",
        "Original measurements, context, named times and bounded follow-up "
        "search independently reconstructed; no diagnosis or missed care inferred.",
        canonical.claim,
    )
