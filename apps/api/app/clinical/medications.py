"""Source-specific medication assertions and reproducible reconciliation relationships."""

import re
from collections import defaultdict
from datetime import date

from app.clinical.claims import ClaimTime, ClinicalClaim
from app.clinical.medication_identity import MedicationIdentity, medication_identity
from app.clinical.relationship_models import RelationshipEvidence, TemporalOrdering
from app.clinical.rules import anchor, instant
from app.clinical.spans import source_anchor, statements
from app.clinical.temporal import reference_day
from app.core.provenance import digest
from app.schemas.investigation import Anchor, Candidate, SourceRecord

LIMITATIONS = [
    "Orders, copied lists and patient reports do not prove dispensing, ingestion or causality.",
    "Document event/authoring times do not necessarily date exposure or instruction applicability.",
    "Unretrieved records, exact doses taken and undocumented restart decisions remain unknown.",
]
ALTERNATIVES = [
    "Planned changes, stale lists or incomplete retrospective histories may explain the records."
]


def identities(records: list[SourceRecord]) -> dict[str, MedicationIdentity]:
    return {
        r.source.id: identity
        for r in records
        if r.source.type == "medication"
        and r.representation == "source"
        and (identity := medication_identity(r.data))
    }


def medication_assertions(record: SourceRecord, records: list[SourceRecord]) -> list[ClinicalClaim]:
    if record.representation != "source":
        return []
    products = identities(records)
    if record.source.type == "medication":
        identity = products.get(record.source.id)
        if not identity:
            return []
        status = str(record.data.get("status") or "unknown")
        copied = not record.data.get("ordered_at")
        return [
            _assertion(
                record,
                anchor(record, "status"),
                identity,
                "listed_active" if copied and status == "active" else status,
                "copied_list" if copied else "order",
                "unknown" if copied else "ordered_at",
            )
        ]
    if record.source.type != "document":
        return []
    text = record.data.get("text_content") or ""
    if len(text) > 100000:
        return []
    unique = {p.model_dump_json(): p for p in products.values()}
    results = []
    for start, end in statements(text):
        passage = text[start:end]
        if len(passage) > 2000:
            continue
        matched = [
            p
            for p in unique.values()
            if re.search(rf"(?<![\w-]){re.escape(p.ingredient)}(?![\w-])", passage, re.I)
        ]
        # A dose/history statement without a drug name needs a unique encounter-linked product.
        if not matched and re.search(
            r"\b(?:last dose|missing (?:several )?doses|exposure uncertain)\b", passage, re.I
        ):
            matched = list(
                {
                    p.model_dump_json(): p
                    for r in records
                    if r.source.id in products
                    and r.data.get("encounter_id") == record.data.get("encounter_id")
                    for p in [products[r.source.id]]
                }.values()
            )
            if len(matched) != 1:
                matched = []
        for product in matched:
            # Ingredient-only language cannot resolve multiple strengths/formulations/routes.
            variants = [p for p in unique.values() if p.ingredient == product.ingredient]
            if len(variants) > 1:
                continue
            # Actions belong to the named product's clause, not a different drug
            # in the same sentence (e.g. stop A and prescribe B).
            names = "|".join(re.escape(p.ingredient) for p in unique.values())
            clauses = re.split(rf";|\band\s+(?=(?:{names})\b)", passage, flags=re.I)
            named = any(re.search(rf"\b(?:{names})\b", clause, re.I) for clause in clauses)
            scope = (
                " ".join(
                    clause
                    for clause in clauses
                    if re.search(rf"\b{re.escape(product.ingredient)}\b", clause, re.I)
                )
                if named
                else passage
            )
            if not scope:
                continue
            if re.search(r"\b(?:family history|mother|father|sister|brother)\b", scope, re.I):
                # Do not attribute relatives' medication use to the selected patient.
                continue
            stated_product = medication_identity(
                {"medication_name": scope, "generic_name": product.ingredient}
            )
            if stated_product and any(
                getattr(stated_product, field)
                and getattr(product, field)
                and getattr(stated_product, field) != getattr(product, field)
                for field in ("strength", "formulation")
            ):
                continue
            patterns = [
                ("discontinued", r"\b(?:discontinued|stop(?:ped)?)\b", "clinician_record"),
                ("held", r"\b(?:hold|holding|held)\b", "clinician_record"),
                ("restart_order", r"\b(?:restart(?:ed)?|resum(?:e|ed))\b", "clinician_record"),
                (
                    "reported_use",
                    r"\b(?:reports? (?:taking|using)|states? (?:she |he )?takes?|"
                    r"says (?:she |he )?may have taken|patient.reported)\b",
                    "patient_report",
                ),
                (
                    "listed_active",
                    r"\b(?:list.*(?:active|includes)|marked active)\b",
                    "copied_list",
                ),
                (
                    "exposure_unknown",
                    r"\b(?:uncertain|unsure|cannot (?:recall|confirm|state)|unable to confirm|"
                    r"does not establish|do not establish|not proof|no administration record|"
                    r"may have taken)\b",
                    "clinician_record",
                ),
                (
                    "administration_documented",
                    r"\b(?:administered|administration documented)\b",
                    "administration",
                ),
            ]
            if (
                re.search(r"\b(?:resume[ds]?|restart[eds]*)\b", scope, re.I)
                and re.search(r"\b(?:hold|holding|held)\b", scope, re.I)
                and re.search(r"\b(?:but|until)\b", scope, re.I)
            ):
                results.append(
                    _assertion(
                        record,
                        source_anchor(record, "text_content", start, end),
                        product,
                        "hold_restart_text",
                        "clinician_record",
                        "event_at",
                    )
                )
            for state, pattern, origin in patterns:
                match = re.search(pattern, scope, re.I)
                if not match:
                    continue
                if state in {
                    "discontinued",
                    "held",
                    "restart_order",
                    "administration_documented",
                } and re.search(r"\b(?:if|consider|may need)\b", scope, re.I):
                    continue
                if state in {
                    "discontinued",
                    "held",
                    "restart_order",
                    "administration_documented",
                } and re.search(
                    r"\b(?:not|no|never|do not)\s+(?:\w+\s+){0,2}$", scope[: match.start()], re.I
                ):
                    continue
                results.append(
                    _assertion(
                        record,
                        source_anchor(record, "text_content", start, end),
                        product,
                        state,
                        origin,
                        "event_at",
                    )
                )
                if len(results) >= 24:
                    return results
    return results


def _assertion(
    record: SourceRecord,
    citation: Anchor,
    identity: MedicationIdentity,
    state: str,
    origin: str,
    event_field: str,
) -> ClinicalClaim:
    reference = record.data.get(event_field)
    day = reference_day(reference)
    return ClinicalClaim(
        id="MC-"
        + digest(
            {
                "anchor": citation.model_dump(mode="json"),
                "identity": identity.model_dump(),
                "state": state,
            }
        )[:24],
        patient_id=record.data.get("patient_id"),
        anchor=citation,
        concept=identity.model_dump_json(),
        qualifiers=[
            f"effective_{match[1]}:{match[2]}"
            for match in re.finditer(
                r"\b(until|through|on|from|beginning)\s+(\d{4}-\d{2}-\d{2})\b",
                citation.quote or "",
                re.I,
            )
        ],
        original_concept=identity.ingredient,
        assertion="medication_status",
        value=state,
        origin=origin,  # type: ignore[arg-type]
        attribution="patient_report" if origin == "patient_report" else "clinician_record",
        certainty="uncertain" if state in {"exposure_unknown", "reported_use"} else "asserted",
        recorded_status=state,
        source_status=record.data.get("status"),
        event_time_field=None if event_field == "unknown" else event_field,
        documentation_time_field="authored_at" if record.source.type == "document" else None,
        timestamps={k: v for k, v in record.data.items() if k.endswith("_at")},
        time=ClaimTime(
            start=day,
            end=day,
            precision="day" if day else "unknown",
            reference=reference,
            basis="encounter" if day else "unknown",
        ),
        limitations=LIMITATIONS,
    )


def medication_relationships(records: list[SourceRecord]) -> list[Candidate]:
    rows = [r for r in records[:100] if r.representation == "source"]
    groups: dict[tuple[str, str], list[tuple[ClinicalClaim, SourceRecord]]] = defaultdict(list)
    for row in rows:
        for assertion in medication_assertions(row, rows):
            groups[(assertion.patient_id or "", assertion.concept)].append((assertion, row))
    candidates = []
    for (_, concept), assertions in sorted(groups.items()):
        orders = [(a, r) for a, r in assertions if r.source.type == "medication"]
        docs = [(a, r) for a, r in assertions if r.source.type == "document"]
        if not orders or not docs:
            continue
        stopped = [
            (a, r)
            for a, r in assertions
            if a.value in {"held", "discontinued", "hold_restart_text"}
        ]
        later = [
            (a, r)
            for a, r in docs
            if a.value
            in {
                "reported_use",
                "listed_active",
                "restart_order",
                "exposure_unknown",
                "administration_documented",
            }
        ]
        if not later:
            continue
        if not stopped:
            if not any(a.value == "exposure_unknown" for a, _ in later):
                continue
            stopped = orders[:1]
        stop, stop_row = min(
            stopped,
            key=lambda x: (
                x[0].value != "hold_restart_text",
                x[1].source.type != "medication",
                str(x[0].time.reference or "~"),
                x[0].id,
            ),
        )
        overlapping = next(
            (
                (held, held_row)
                for held, held_row in stopped
                if held.value == "held"
                and any(
                    _planned_overlap(held, restart)
                    for restart, _ in later
                    if restart.value == "restart_order"
                )
            ),
            None,
        )
        if overlapping:
            stop, stop_row = overlapping
        following = [
            (a, r)
            for a, r in later
            if instant(a.time.reference)
            and instant(stop.time.reference)
            and _ordered(stop.time.reference, a.time.reference, equal=True)
        ]
        # A signed later restart can explain a temporary hold; do not call that a conflict.
        restarts = [(a, r) for a, r in following if a.value == "restart_order"]
        kind = "Documented medication-history uncertainty"
        if overlapping:
            kind = "Overlapping recorded hold/restart instructions"
        elif stop.value == "hold_restart_text":
            kind = "Conflicting recorded hold/restart instruction text"
        elif (
            stop.value in {"held", "discontinued"}
            and any(a.value in {"reported_use", "listed_active"} for a, _ in following)
            and not restarts
        ):
            kind = "Reported/listed medication use differs from stop documentation"
        elif restarts:
            kind = "Documented hold followed by restart; effective exposure remains unknown"
        if not following:
            continue
        # Choose decisive source roles rather than pooling whole charts.
        selected = [(stop, stop_row)]
        for a, r in sorted(
            following,
            key=lambda x: (
                x[0].value != "reported_use",
                x[0].value != "exposure_unknown",
                str(x[0].time.reference),
                x[0].id,
            ),
        ):
            if len(selected) >= 5:
                break
            if not any(old.anchor == a.anchor for old, _ in selected):
                selected.append((a, r))
        if len({r.source.id for _, r in selected}) < 2:
            continue
        # Ground narrative product identity with an original structured order.
        identity_row = min((r for _, r in orders), key=lambda r: r.source.id)
        citations = [a.anchor for a, _ in selected]
        for a, r in selected:
            if a.event_time_field and r.data.get(a.event_time_field):
                citations.append(anchor(r, a.event_time_field))
            if r.source.type == "document":
                context = next(
                    (
                        order
                        for _, order in orders
                        if order.data.get("encounter_id") == r.data.get("encounter_id")
                    ),
                    None,
                )
                if context and context.source != identity_row.source:
                    citations.append(anchor(context, "medication_name"))
        for field in ["medication_name", "generic_name", "dose", "dose_unit", "route"]:
            if identity_row.data.get(field) is not None:
                citations.append(anchor(identity_row, field))
        citations = list({a.model_dump_json(): a for a in citations}.values())
        if len(citations) > 20:
            continue
        ordering = [
            TemporalOrdering(
                earlier_assertion_id=stop.id,
                earlier_field=stop.event_time_field,
                later_assertion_id=a.id,
                later_field=a.event_time_field,
            )
            for a, _ in selected[1:]
            if stop.event_time_field
            and a.event_time_field
            and _ordered(stop.time.reference, a.time.reference)
        ]
        product = MedicationIdentity.model_validate_json(concept)
        candidates.append(
            Candidate(
                type="clinical_relationship",
                title=kind,
                claim=f"{kind} for {product.ingredient}: "
                + "; ".join(f"{r.source.id} documents {a.value}" for a, r in selected)
                + ". Actual exposure, exact applicability and causality remain unestablished.",
                claim_kind="observation",
                rule="clinical_relationship",
                anchors=citations,
                relationship=RelationshipEvidence(
                    relationship_type="medication_reconciliation",
                    assertions=[a for a, _ in selected],
                    supporting_assertion_ids=[a.id for a, _ in selected],
                    temporal_ordering=ordering,
                    unresolved_questions=[
                        "Which instructions applied and what doses were actually taken?"
                    ],
                ),
                alternatives=ALTERNATIVES,
                limitations=LIMITATIONS,
            )
        )
        if len(candidates) == 6:
            break
    return candidates


def _ordered(earlier: str | None, later: str | None, equal: bool = False) -> bool:
    left, right = instant(earlier), instant(later)
    return bool(left and right and (left <= right if equal else left < right))


def _planned_overlap(held: ClinicalClaim, restart: ClinicalClaim) -> bool:
    try:
        until = next(
            (
                date.fromisoformat(q.split(":", 1)[1])
                for q in held.qualifiers
                if q.startswith(("effective_until:", "effective_through:"))
            ),
            None,
        )
        beginning = next(
            (
                date.fromisoformat(q.split(":", 1)[1])
                for q in restart.qualifiers
                if q.startswith(("effective_on:", "effective_from:", "effective_beginning:"))
            ),
            None,
        )
    except ValueError:
        return False
    return bool(until and beginning and beginning < until)


def laboratory_questions(
    medications: list[Candidate], laboratory: list[Candidate]
) -> list[Candidate]:
    """Consume laboratory specialist evidence without granting the medication role lab access."""
    questions = []
    for medication in medications:
        if (
            not medication.relationship
            or medication.relationship.relationship_type != "medication_reconciliation"
        ):
            continue
        times = [t for a in medication.relationship.assertions if (t := instant(a.time.reference))]
        if not times:
            continue
        for laboratory_finding in laboratory:
            collections = [
                t
                for a in laboratory_finding.anchors
                if a.field == "specimen_collected_at" and (t := instant(a.expected))
            ]
            if not any(min(times) <= t <= max(times) for t in collections):
                continue
            anchors = list(
                {
                    a.model_dump_json(): a
                    for a in [medication.anchors[0], *laboratory_finding.anchors]
                }.values()
            )
            if len(anchors) > 20:
                continue
            questions.append(
                Candidate(
                    type="clinical_relationship",
                    title="Medication and laboratory documentation overlap",
                    claim="Laboratory measurements occur within the medication documentation "
                    "interval; exposure and causality require review.",
                    claim_kind="hypothesis",
                    rule="interpretation",
                    anchors=anchors,
                    alternatives=[
                        "Illness, hydration and other exposures require source-based review."
                    ],
                    limitations=LIMITATIONS,
                )
            )
            break
        if len(questions) == 2:
            break
    return questions
