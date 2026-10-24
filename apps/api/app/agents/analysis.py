"""Reusable deterministic analyses of retrieved records; no hidden answer identifiers."""

from app.clinical.hypotheses import assess_hypotheses
from app.clinical.laboratory import analyte_key
from app.clinical.reasoning import structured_contradictions
from app.clinical.rules import anchor as anchor
from app.clinical.rules import contradictions as legacy_contradictions
from app.clinical.rules import instant as instant
from app.schemas.investigation import Candidate, Hypothesis, SourceRecord, TimelineEvent


def contradictions(
    notes: list[SourceRecord], events: list[SourceRecord], reasoning: str = "legacy"
) -> list[Candidate]:
    return (structured_contradictions if reasoning == "structured" else legacy_contradictions)(
        notes, events
    )


TIME_FIELDS = (
    "occurred_at",
    "documented_at",
    "started_at",
    "ended_at",
    "event_at",
    "authored_at",
    "specimen_collected_at",
    "reported_at",
    "ordered_at",
    "start_at",
    "end_at",
    "performed_at",
    "appointment_at",
    "issued_at",
    "diagnosed_at",
    "onset_at",
)
PRIMARY = {
    "encounter": "started_at",
    "clinical_event": "occurred_at",
    "document": "event_at",
    "observation": "specimen_collected_at",
    "medication": "start_at",
    "imaging_study": "performed_at",
    "referral": "ordered_at",
    "diagnostic_report": "issued_at",
    "diagnosis": "diagnosed_at",
    "symptom": "onset_at",
}


def timeline(records: list[SourceRecord]) -> list[TimelineEvent]:
    events = []
    for record in records:
        field = PRIMARY.get(record.source.type, "occurred_at")
        raw = record.data.get(field)
        events.append(
            TimelineEvent(
                id=f"TL-{record.source.type}-{record.source.id}",
                source=record.source,
                timestamp=raw,
                timestamp_type=field,
                precision="unknown" if raw is None else "day" if len(raw) == 10 else "instant",
                timestamps={k: record.data[k] for k in TIME_FIELDS if k in record.data},
                title=str(
                    next(
                        (
                            record.data[k]
                            for k in [
                                "title",
                                "description",
                                "test_name",
                                "medication_name",
                                "reason",
                                "department",
                            ]
                            if record.data.get(k)
                        ),
                        record.source.id,
                    )
                ),
            )
        )
    # Partial days and unknown times remain explicit; never replace with invented midnight.
    events.sort(
        key=lambda e: (
            e.timestamp is None,
            parsed.isoformat() if (parsed := instant(e.timestamp)) else e.timestamp or "",
            e.id,
        )
    )
    return events


def lab_changes(records: list[SourceRecord]) -> list[Candidate]:
    groups: dict[tuple[str, str, str], list[SourceRecord]] = {}
    for record in records:
        if record.data.get("value_numeric") is None or not instant(
            record.data.get("specimen_collected_at"),
        ):
            continue
        key = analyte_key(record)
        if key is None:
            continue
        groups.setdefault(key, []).append(record)
    findings = []
    for group in groups.values():
        group.sort(key=lambda r: (instant(r.data["specimen_collected_at"]), r.source.id))
        first, last = group[0], group[-1]
        if first.data["value_numeric"] == last.data["value_numeric"]:
            continue
        findings.append(
            Candidate(
                type="laboratory_change",
                title=f"Recorded change in {first.data['test_name']}",
                claim=f"{first.source.id} and {last.source.id} record different values.",
                claim_kind="observation",
                rule="lab_change",
                anchors=[
                    anchor(r, f)
                    for r in [first, last]
                    for f in [
                        "test_name",
                        "test_code",
                        "value_numeric",
                        "unit",
                        "specimen_collected_at",
                        "reference_range_low",
                        "reference_range_high",
                    ]
                    if f in r.data and r.data[f] is not None
                ],
                limitations=[
                    "A numerical change alone does not establish clinical significance or cause."
                ],
            )
        )
    return findings


def medication_observations(records: list[SourceRecord]) -> list[Candidate]:
    return [
        Candidate(
            type="medication_change",
            title=f"Documented medication status: {r.data['medication_name']}",
            claim=f"{r.source.id} documents medication status {r.data['status']}.",
            claim_kind="observation",
            rule="field_observation",
            anchors=[
                anchor(r, f)
                for f in [
                    "medication_name",
                    "status",
                    "dose",
                    "dose_unit",
                    "ordered_at",
                    "start_at",
                    "end_at",
                ]
                if f in r.data
            ],
            limitations=[
                "Orders and recorded medication periods do not establish dispensing, "
                "administration, adherence or causation."
            ],
        )
        for r in records
    ]


def followups(referrals: list[SourceRecord]) -> list[Candidate]:
    return [
        Candidate(
            type="missing_evidence",
            title="Follow-up status requires reconciliation",
            claim=f"Referral {r.source.id} has recorded status {r.data['status']}; "
            "the available record does not establish completion.",
            claim_kind="interpretation",
            rule="interpretation",
            anchors=[
                anchor(r, f)
                for f in ["status", "ordered_at", "appointment_at"]
                if r.data.get(f) is not None
            ],
            limitations=[
                "Missing completion documentation is not proof of missed care. "
                "Care may have occurred elsewhere; future appointments are not overdue."
            ],
        )
        for r in referrals
        if r.data.get("status") in {"ordered", "scheduled", "unknown", "no_show"}
    ]


def challenge(candidates: list[Candidate]) -> list[Hypothesis]:
    return assess_hypotheses(candidates)
