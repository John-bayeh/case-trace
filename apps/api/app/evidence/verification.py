"""Resolve every assertion against hospital records, not model self-confidence."""

from app.clinical.laboratory import analyte_key, range_description
from app.clinical.ports import SourceResolver
from app.clinical.reasoning import structured_contradictions
from app.clinical.rules import contradictions, instant, onset_pair
from app.clinical.series import record_series
from app.evidence.longitudinal import verify_longitudinal
from app.evidence.provenance import anchor_matches
from app.evidence.relationships import verify_relationship
from app.hospital.errors import HospitalError
from app.schemas.investigation import Candidate, Check, SourceRecord, Verification


class EvidenceVerifier:
    def __init__(self, clinical: SourceResolver, patient_id: str, reasoning: str = "legacy"):
        self.clinical, self.patient_id = clinical, patient_id
        self.reasoning = reasoning

    async def verify(self, candidate: Candidate) -> tuple[Verification, str]:
        if candidate.longitudinal is not None or candidate.rule == "longitudinal_followup":
            return await verify_longitudinal(self.clinical, self.patient_id, candidate)
        if candidate.relationship is not None or candidate.rule == "clinical_relationship":
            return await verify_relationship(self.clinical, self.patient_id, candidate)
        checks = []
        records: dict[str, SourceRecord] = {}
        identities = [(a.source.type, a.source.id, a.field) for a in candidate.anchors]
        if len(set(identities)) != len(identities) or (
            candidate.rule == "field_observation"
            and not any(a.relationship == "supports" for a in candidate.anchors)
        ):
            return Verification(
                status="rejected",
                checks=[
                    Check(
                        type="evidence_completeness",
                        status="failed",
                        message="Distinct anchors and at least one supporting anchor are required.",
                    )
                ],
                classification="INSUFFICIENT_EVIDENCE",
            ), candidate.claim
        for anchor in candidate.anchors:
            try:
                source = await self.clinical.resolve(self.patient_id, anchor.source)
                records[f"{anchor.source.type}:{anchor.source.id}"] = source
                valid = anchor_matches(source, anchor)
                checks.append(
                    Check(
                        type="source_existence",
                        status="passed" if valid else "failed",
                        message=f"{anchor.source.id}: version, hash, encounter and field anchor",
                    )
                )
            except HospitalError:
                checks.append(
                    Check(
                        type="source_existence",
                        status="failed",
                        message="Source or registered asset unavailable in patient scope.",
                    )
                )
        if any(c.status == "failed" for c in checks):
            return Verification(
                status="rejected", checks=checks, classification="INSUFFICIENT_EVIDENCE"
            ), candidate.claim
        rows = list(records.values())
        valid = False
        claim = candidate.claim
        classification = "INSUFFICIENT_EVIDENCE"
        if candidate.rule == "record_series" and candidate.claim_kind == "observation":
            # Rebuild the proposition from independently resolved originals. Never
            # promote arbitrary candidate prose just because its citations exist.
            supplied = [a.model_dump() for a in candidate.anchors]
            matched_series = next(
                (
                    c
                    for c in record_series(rows)
                    if c.type == candidate.type
                    and len(c.anchors) == len(supplied)
                    and all(a.model_dump() in supplied for a in c.anchors)
                ),
                None,
            )
            valid = matched_series is not None
            if matched_series:
                claim = matched_series.claim
        elif (
            candidate.rule == "field_observation"
            and candidate.claim_kind == "observation"
            and candidate.type in {"medication_change", "clinical_relationship"}
        ):
            valid = True
            claim = "; ".join(
                f"{a.source.id}.{a.field} = {a.expected}"
                for a in candidate.anchors
                if a.relationship == "supports"
            )
        elif (
            candidate.rule == "lab_change"
            and candidate.type == "laboratory_change"
            and candidate.claim_kind == "observation"
            and len(rows) == 2
        ):
            first, last = rows
            a, b = first.data, last.data
            at, bt = (
                instant(a.get("specimen_collected_at")),
                instant(b.get("specimen_collected_at")),
            )
            complete = all(
                any(
                    anchor.source == row.source and anchor.field == field
                    for anchor in candidate.anchors
                )
                for row in rows
                for field in ["test_name", "value_numeric", "unit", "specimen_collected_at"]
            )
            valid = bool(
                complete
                and first.source.type == last.source.type == "observation"
                and analyte_key(first) is not None
                and analyte_key(first) == analyte_key(last)
                and a.get("value_numeric") is not None
                and b.get("value_numeric") is not None
                and a["value_numeric"] != b["value_numeric"]
                and at
                and bt
                and at < bt
            )
            claim = (
                f"{a.get('test_name')}: {a.get('value_numeric')} {a.get('unit')} "
                f"({first.source.id}, {a.get('specimen_collected_at')}) to "
                f"{b.get('value_numeric')} {b.get('unit')} "
                f"({last.source.id}, {b.get('specimen_collected_at')})."
                f" {range_description(first)} {range_description(last)}"
            )
        elif (
            candidate.rule == "onset_conflict"
            and candidate.claim_kind == "chronology"
            and candidate.type == "timeline_contradiction"
        ):
            notes = [
                r
                for r in rows
                if r.source.type == "document"
                and any(
                    a.source == r.source and a.relationship == "supports" for a in candidate.anchors
                )
            ]
            events = [r for r in rows if r.source.type == "clinical_event"]
            if self.reasoning == "structured":
                regenerated = structured_contradictions(
                    [r for r in rows if r.source.type == "document"], events
                )
                # All decisive source passages AND chronology fields must be cited.
                supplied = [a.model_dump() for a in candidate.anchors]
                matched = next(
                    (
                        c
                        for c in regenerated
                        if c.rule == "onset_conflict"
                        and all(a.model_dump() in supplied for a in c.anchors)
                    ),
                    None,
                )
                valid = matched is not None
                if matched:
                    claim = matched.claim
            else:
                valid = len(notes) == len(events) == 1 and onset_pair(notes[0], events[0])
                if valid:
                    regenerated_legacy = contradictions(notes, events)
                    required = regenerated_legacy[0].anchors
                    valid = all(
                        any(
                            a.source == r.source and a.field == r.field and a.quote == r.quote
                            for a in candidate.anchors
                        )
                        for r in required
                    )
                    claim = regenerated_legacy[0].claim
            if valid:
                classification = "VERIFIED_CONTRADICTION"
        checks.append(
            Check(
                type="relationship_verification",
                status="passed" if valid else "inconclusive",
                message="Deterministic proposition check; clinical interpretations require review.",
            )
        )
        return Verification(
            status="verified" if valid else "inconclusive",
            checks=checks,
            classification=classification
            if classification == "VERIFIED_CONTRADICTION"
            else "SUPPORTED_OBSERVATION"
            if valid
            else "INSUFFICIENT_EVIDENCE",
        ), claim
