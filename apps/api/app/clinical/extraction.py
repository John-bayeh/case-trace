"""Bounded deterministic assertions from original tool-returned narrative fields."""

import re

from app.clinical.claims import ClaimTime, ClinicalClaim
from app.clinical.concepts import mentions
from app.clinical.spans import source_anchor, statements
from app.clinical.temporal import narrative_time, reference_day
from app.core.provenance import digest
from app.schemas.investigation import Anchor, SourceRecord

MAX_TEXT = 100000
MAX_CLAIMS = 64


def context_priority(claim: ClinicalClaim) -> tuple[bool, int]:
    """Prefer an explicit recorded assertion over a bare heading or indication."""
    return (
        not bool(
            re.search(
                r"\b(?:present|persists?|reports?|continues?|remains?|observed|describes?)\b",
                claim.anchor.quote or "",
                re.I,
            )
        ),
        claim.anchor.char_start or 0,
    )


def structured_claims(record: SourceRecord) -> list[ClinicalClaim]:
    """Recorded structured states; never infer administration or completion."""
    kind = record.source.type
    mapping = {
        "observation": ("value_numeric", "test_name", "specimen_collected_at", "observation"),
        "medication": ("status", "medication_name", "ordered_at", "medication_status"),
        "referral": ("status", "reason", "ordered_at", "followup_status"),
    }
    if kind not in mapping:
        return []
    field, concept_field, time_field, assertion = mapping[kind]
    data = record.data
    if data.get(field) is None or not data.get(concept_field):
        return []
    reference = data.get(time_field)
    day = reference_day(reference)
    item = Anchor(
        source=record.source,
        source_version=record.source_version,
        source_hash=record.source_hash,
        encounter_id=data.get("encounter_id"),
        field=field,
        expected=data[field],
    )
    return [
        ClinicalClaim(
            id="CL-"
            + digest(
                {"source": record.source.model_dump(), "hash": record.source_hash, "field": field}
            )[:24],
            patient_id=data.get("patient_id"),
            anchor=item,
            concept=str(data.get("test_code") or data[concept_field]),
            original_concept=str(data[concept_field]),
            assertion=assertion,  # type: ignore[arg-type]
            value=data[field],
            unit=data.get("unit"),
            recorded_status=data.get("status"),
            origin="observation" if kind == "observation" else "order",
            source_status=data.get("status"),
            event_time_field=time_field,
            documentation_time_field="reported_at" if kind == "observation" else None,
            time=ClaimTime(
                start=day,
                end=day,
                precision="day" if day else "unknown",
                reference=reference,
                basis="explicit",
            ),
            timestamps={key: value for key, value in data.items() if key.endswith("_at")},
            limitations=[
                "Recorded status does not establish administration, adherence or care delivery."
            ]
            if kind != "observation"
            else ["A recorded measurement does not establish clinical significance."],
        )
    ]


def extract_claims(record: SourceRecord) -> list[ClinicalClaim]:
    if record.representation != "source":
        return []
    if record.source.type in {"observation", "medication", "referral"}:
        return structured_claims(record)
    field = "text_content" if record.source.type == "document" else "description"
    text = record.data.get(field)
    if not isinstance(text, str):
        return []
    # No clipped source fields or clipped statements masquerade as complete assertions.
    if len(text) > MAX_TEXT:
        return []
    reference = record.data.get("occurred_at") or record.data.get("event_at")
    result = []
    for start, end in statements(text):
        passage = text[start:end]
        heading = re.match(r"^([A-Za-z ]{2,40}):", passage)
        section = record.data.get("section") or (heading[1] if heading else None)
        if len(passage) > 2000:
            continue
        # Clause-local assertion scope prevents 'denies fever; cough persists' contamination.
        for concept, match in mentions(passage):
            left = (
                max(passage.rfind(";", 0, match.start()), passage.rfind(":", 0, match.start())) + 1
            )
            right = passage.find(";", match.end())
            clause = passage[left : right if right >= 0 else len(passage)]
            before = passage[left : match.start()]
            after = passage[match.end() : right if right >= 0 else len(passage)]
            # Contrast starts a new assertion scope, unlike a coordinated denial.
            before = re.split(r"\b(?:but|however|although)\b", before, flags=re.I)[-1]
            negative = bool(
                re.search(
                    r"\b(?:no|denies|denied|without|negative for)\s+(?:\w+\s+){0,3}$", before, re.I
                )
            )
            uncertain = bool(
                re.search(
                    r"\b(?:possible|possibly|uncertain|suspected)\b|"
                    r"\b(?:may|might)\s+(?:be|have|reflect|represent|contribute|cause|explain|amplify)\b",
                    clause,
                    re.I,
                )
            )
            hypothetical = bool(re.search(r"\b(?:rule out|r/o|if|consider)\b", clause, re.I)) or (
                str(section or "").casefold() in {"plan", "recommendation", "recommendations"}
            )
            family = (
                bool(
                    re.search(r"\b(?:family history|mother|father|sister|brother)\b", clause, re.I)
                )
                or "family history" in str(section or "").casefold()
            )
            recurrence = bool(
                re.search(
                    r"\b(?:recurrent|intermittent|similar|previous episode|prior episode)"
                    r"\s+(?:\w+\s+){0,2}$",
                    before,
                    re.I,
                )
            ) or bool(re.match(r"\s+(?:is\s+)?(?:recurrent|intermittent)\b", after, re.I))
            first = bool(re.search(r"\bfirst\b", clause, re.I)) or bool(
                re.search(
                    r"\bno\s+(?:\w+\s+){0,2}" + re.escape(match[0]) + r"\s+before", passage, re.I
                )
            )
            new = bool(re.search(r"\b(?:new episode|another episode|this episode)\b", clause, re.I))
            onset = bool(
                re.search(
                    r"\b(?:began|started|onset|first noticed|first experienced)\b", clause, re.I
                )
            )
            assertion = (
                "impression"
                if concept in {"pneumonia", "asthma"}
                else "absence"
                if negative
                else "resolution"
                if re.search(r"\b(?:resolved|resolution|subsided)\b", after, re.I)
                else "worsening"
                if re.search(r"\b(?:worsen\w*|deteriorat\w*)\b", clause, re.I)
                else "recurrence"
                if recurrence
                else "onset"
                if onset
                else "presence"
            )
            historical = recurrence or bool(
                re.search(r"\b(?:history of|had|previously|earlier|last month)\b", clause, re.I)
            )
            when = narrative_time(clause, reference)
            prior_absence = negative and bool(re.search(r"\bbefore\b", clause, re.I))
            if prior_absence:
                when = ClaimTime(basis="historical", reference=reference, original=clause)
                historical = True
            if not onset and not historical and when.precision == "unknown":
                day = reference_day(reference)
                when = ClaimTime(
                    start=day,
                    end=day,
                    precision="day" if day else "unknown",
                    basis="encounter",
                    reference=reference,
                )
            modifier_before = re.split(r"\b(?:and|but)\b|[,;:]", before, flags=re.I)[-1]
            modifier_after = re.split(r"\b(?:and|but)\b|[,;:]", after, flags=re.I)[0]
            modifier_text = " ".join(modifier_before.split()[-3:] + modifier_after.split()[:3])
            qualifiers = [
                q
                for q in ("persistent", "dry", "productive", "intermittent", "recurrent")
                if re.search(rf"\b{q}\b", modifier_text, re.I)
            ]
            span = source_anchor(record, field, start, end)
            identity = digest(
                {
                    "source": record.source.model_dump(),
                    "hash": record.source_hash,
                    "offset": start + match.start(),
                    "concept": concept,
                }
            )[:24]
            result.append(
                ClinicalClaim(
                    id=f"CL-{identity}",
                    patient_id=record.data.get("patient_id"),
                    anchor=span,
                    concept=concept,
                    original_concept=match[0],
                    qualifiers=qualifiers,
                    assertion=assertion,  # type: ignore[arg-type]
                    subject="family" if family else "patient",
                    attribution="patient_report"
                    if re.search(r"\b(?:reports?|denies|noticed|experienced)\b", clause, re.I)
                    else "clinician_record",
                    polarity="negative" if negative or assertion == "resolution" else "positive",
                    certainty="hypothetical"
                    if hypothetical
                    else "uncertain"
                    if uncertain
                    else "asserted",
                    temporality="historical"
                    if historical
                    else "current"
                    if not onset
                    else "unknown",
                    time=when,
                    episode_id=record.data.get("episode_id"),
                    episode_scope="first"
                    if first
                    else "recurrent"
                    if recurrence
                    else "new"
                    if new
                    else "unspecified",
                    section=section,
                    origin="patient_report"
                    if re.search(
                        r"\bpatient\s+(?:reports?|describes?|states?|denies)\b", clause, re.I
                    )
                    else "clinician_interpretation"
                    if assertion == "impression"
                    else "clinician_record",
                    source_status=record.data.get("status"),
                    event_time_field="occurred_at"
                    if record.source.type == "clinical_event"
                    else "event_at",
                    documentation_time_field="documented_at"
                    if record.source.type == "clinical_event"
                    else "authored_at",
                    timestamps={
                        key: value for key, value in record.data.items() if key.endswith("_at")
                    },
                    limitations=[
                        "Rule-based vocabulary and assertion scope are intentionally limited."
                    ]
                    + (
                        [
                            "Relative approximate bounds are heuristic "
                            "(+/-3 days for weeks, +/-1 for days), not recorded limits."
                        ]
                        if when.basis == "relative" and when.precision == "approximate"
                        else []
                    )
                    + (
                        [
                            "Early/mid/late month use calendar thirds; "
                            "absent years use the encounter year."
                        ]
                        if when.precision == "month"
                        else []
                    )
                    + (["No reliable temporal reference."] if when.precision == "unknown" else []),
                )
            )
            if len(result) >= MAX_CLAIMS:
                return result
    return result


def validate_model_claim(record: SourceRecord, proposed: ClinicalClaim) -> bool:
    """Typed extension seam. A model cannot introduce unsupported semantic/date attributes.

    Until a broader verifier is available, only independently reproducible rule
    assertions are accepted. This is validation, not a claim of live model extraction.
    """
    from app.evidence.provenance import anchor_matches

    if proposed.patient_id != record.data.get("patient_id") or not anchor_matches(
        record, proposed.anchor
    ):
        return False
    expected = proposed.model_dump(exclude={"id", "extraction_method"})
    return any(
        c.model_dump(exclude={"id", "extraction_method"}) == expected
        for c in extract_claims(record)
    )
