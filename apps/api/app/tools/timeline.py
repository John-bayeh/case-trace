"""Bounded aggregation of recorded chronology, with original sources intact."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.hospital.errors import HospitalError
from app.schemas.investigation import SourceRecord, SourceRef, SourceType, TimelineEvent, ToolResult
from app.tools.inputs import TimelineInput
from app.tools.results import result_for, validate_source

if TYPE_CHECKING:
    from app.tools.clinical import ClinicalTools

CATEGORIES: dict[str, tuple[SourceType, str]] = {
    "encounters": ("encounter", "started_at"),
    "events": ("clinical_event", "occurred_at"),
    "observations": ("observation", "specimen_collected_at"),
    "medications": ("medication", "start_at"),
    "documents": ("document", "event_at"),
    "imaging_studies": ("imaging_study", "performed_at"),
    "diagnostic_reports": ("diagnostic_report", "issued_at"),
    "referrals": ("referral", "ordered_at"),
    "diagnoses": ("diagnosis", "diagnosed_at"),
    "symptoms": ("symptom", "onset_at"),
}


def project(record: SourceRecord, field: str) -> TimelineEvent:
    raw = record.data.get(field)
    return TimelineEvent(
        id=f"TL-{record.source.type}-{record.source.id}",
        source=record.source,
        timestamp=raw,
        timestamp_type=field,
        precision="unknown" if raw is None else "day" if len(raw) == 10 else "instant",
        timestamps={k: v for k, v in record.data.items() if k.endswith("_at")},
        title=str(
            next(
                (
                    record.data[k]
                    for k in (
                        "title",
                        "description",
                        "test_name",
                        "medication_name",
                        "reason",
                        "department",
                    )
                    if record.data.get(k)
                ),
                record.source.id,
            )
        ),
    )


async def build_timeline(clinical: "ClinicalTools", args: TimelineInput) -> ToolResult:
    if args.encounter_id:
        await clinical.resolve(args.patient_id, SourceRef(type="encounter", id=args.encounter_id))
    entries: list[tuple[SourceRecord, TimelineEvent]] = []
    scanned = 0
    for category in args.include:
        kind, field = CATEGORIES[category]
        offset = 0
        while True:
            filters = args.model_dump(exclude_none=True, exclude={"patient_id", "include"})
            filters.update(limit=100, offset=offset, _sort="asc")
            # An encounter's own ID is its association key.
            if kind == "encounter" and args.encounter_id:
                filters["id"] = filters.pop("encounter_id")
            records, total = await clinical.source.records(kind, args.patient_id, filters)
            for record in records:
                validate_source(record, args.patient_id)
                if record.source.type != kind:
                    raise HospitalError("INVALID_SOURCE_PROVENANCE", 422)
                entries.append((record, project(record, field)))
            scanned += len(records)
            offset += len(records)
            if scanned > 10000:
                raise HospitalError("TIMELINE_SELECTION_TOO_LARGE", 409)
            if offset >= total:
                break
            if not records:
                raise HospitalError("PAGINATION_STALLED", 422)

    def order(entry: tuple[SourceRecord, TimelineEvent]) -> tuple[int, str, str]:
        event = entry[1]
        raw = event.timestamp
        if raw is None:
            return 2, "", event.id
        if event.precision == "day":
            return 1, raw, event.id
        return 0, datetime.fromisoformat(raw).astimezone(UTC).isoformat(), event.id

    # Day-only entries form a separately labelled group, never assumed midnight.
    entries.sort(key=order)
    selected = entries[args.offset : args.offset + args.limit]
    result = result_for([r for r, _ in selected], len(entries), args.offset)
    result.timeline = [e for _, e in selected]
    return result
