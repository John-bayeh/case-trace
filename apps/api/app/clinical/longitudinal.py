"""Source-led laboratory scheduling and one-pass follow-up reassessment; no diagnoses."""

import re
from collections import defaultdict
from typing import Literal

from app.clinical.laboratory import analyte_key, range_description
from app.clinical.longitudinal_models import LongitudinalEvidence, Measurement, SeriesSource
from app.clinical.rules import anchor, instant
from app.core.provenance import digest
from app.schemas.investigation import Candidate, SourceRecord

GROUP_LIMIT = 6
MEASUREMENT_LIMIT = 40
DOCUMENT_LIMIT = 24
SEARCH_LIMIT = 240
CONTEXT_FIELDS = (
    "patient_id",
    "encounter_id",
    "test_code",
    "test_name",
    "unit",
    "specimen",
    "specimen_type",
    "specimen_context",
    "fasting_status",
    "specimen_collected_at",
    "reported_at",
    "reference_range_low",
    "reference_range_high",
    "source_document_id",
    "status",
)
LIMITATIONS = [
    "Repeated abnormalities do not establish a diagnosis, diabetes or causality.",
    "Missing documentation does not prove missed care; external care remains unavailable.",
    "Fasting and specimen context remain unknown unless explicitly recorded on the measurement; "
    "narrative values and source-specific reference intervals are not interchangeable.",
    "Later testing does not establish completion of every recommended action or appropriate care.",
]


def group_key(row: SourceRecord) -> str | None:
    identity = analyte_key(row)
    if (
        row.source.type != "observation"
        or row.representation != "source"
        or not identity
        or row.data.get("value_numeric") is None
        or not instant(row.data.get("specimen_collected_at"))
    ):
        return None
    return digest(
        [
            row.data.get("patient_id"),
            identity,
            [
                row.data.get(k)
                for k in ("specimen", "specimen_type", "specimen_context", "fasting_status")
            ],
        ]
    )


def abnormal(row: SourceRecord) -> bool:
    return range_description(row) in {
        "Below the recorded reference interval.",
        "Above the recorded reference interval.",
    }


def groups(rows: list[SourceRecord]) -> dict[str, list[SourceRecord]]:
    result: dict[str, list[SourceRecord]] = defaultdict(list)
    seen = set()
    for row in rows:
        key = group_key(row)
        if key and row.source.id not in seen:
            result[key].append(row)
            seen.add(row.source.id)
    return {
        key: sorted(values, key=lambda r: (instant(r.data["specimen_collected_at"]), r.source.id))
        for key, values in result.items()
        if sum(abnormal(r) for r in values) >= 2
        and len({r.data.get("encounter_id") for r in values} - {None}) >= 2
        and len({instant(r.data["specimen_collected_at"]) for r in values}) >= 2
    }


def priority(rows: list[SourceRecord]) -> tuple[float, int, float, int]:
    severity = 0.0
    for row in rows:
        value = row.data["value_numeric"]
        low, high = (row.data.get(k) for k in ("reference_range_low", "reference_range_high"))
        for bound, outside in (
            (low, low is not None and value < low),
            (high, high is not None and value > high),
        ):
            if outside and bound is not None:
                severity = max(severity, abs(value - bound) / max(abs(bound), 1))
    values = [r.data["value_numeric"] for r in rows]
    return (
        severity,
        len({r.data.get("encounter_id") for r in rows}),
        (max(values) - min(values)) / max(abs(values[0]), 1),
        len({r.data.get("source_document_id") for r in rows} - {None}),
    )


def schedule(
    rows: list[SourceRecord], limit: int = GROUP_LIMIT
) -> tuple[list[tuple[str, list[SourceRecord]]], list[str]]:
    ranked = sorted(
        groups(rows).items(), key=lambda item: (priority(item[1]), item[0]), reverse=True
    )
    selected: list[tuple[str, list[SourceRecord]]] = []
    deferred: list[str] = []
    for key, values in ranked:
        label = f"{values[0].data['test_name']} [{key[:12]}]"
        if len(values) > MEASUREMENT_LIMIT:
            deferred.append(
                f"Deferred laboratory group {label}: MEASUREMENT_BUDGET_EXHAUSTED "
                f"({len(values)} measurements; none silently removed)."
            )
        elif len(selected) >= limit:
            deferred.append(f"Deferred laboratory group {label}: GROUP_BUDGET_EXHAUSTED.")
        else:
            selected.append((key, values))
    return selected, deferred


def manifest(rows: list[SourceRecord]) -> list[SeriesSource]:
    return [
        SeriesSource(source=r.source, version=r.source_version, hash=r.source_hash)
        for r in sorted(rows, key=lambda r: (r.source.type, r.source.id))
    ]


def related_documents(values: list[SourceRecord], rows: list[SourceRecord]) -> list[SourceRecord]:
    patient = values[0].data.get("patient_id")
    encounters = {r.data.get("encounter_id") for r in values} - {None}
    linked = {r.data.get("source_document_id") for r in values} - {None}
    names = {str(values[0].data.get(k) or "").casefold() for k in ("test_code", "test_name")} - {""}
    return [
        r
        for r in rows
        if r.source.type == "document"
        and r.representation == "source"
        and r.data.get("patient_id") == patient
        and (
            r.source.id in linked
            or r.data.get("encounter_id") in encounters
            or any(
                re.search(
                    r"\b" + re.escape(name) + r"\b", str(r.data.get("text_content") or ""), re.I
                )
                for name in names
            )
        )
    ]


def candidate(
    key: str, values: list[SourceRecord], rows: list[SourceRecord], complete: bool
) -> Candidate:
    documents = sorted(related_documents(values, rows), key=lambda r: r.source.id)
    first_time = instant(values[0].data["specimen_collected_at"])
    last_time = instant(values[-1].data["specimen_collected_at"])
    decisive = []
    recommendations = []
    completed = []
    for row in documents:
        text = str(row.data.get("text_content") or "")
        if len(text) > 2000:
            complete = False
            continue
        at = instant(row.data.get("event_at"))
        if re.search(
            r"\b(?:recommend\w*|plan\w*|follow.up|assessment|glucose|hba1c)\b", text, re.I
        ):
            decisive.append(anchor(row, "text_content"))
        if re.search(
            r"\b(?:recommend\w*|plan\w*)\b[^.]{0,100}\b(?:repeat|follow.up|test\w*)\b"
            r"|\brepeat\b[^.]{0,80}\brecommended\b",
            text,
            re.I,
        ):
            recommendations.append(row)
        # A generic 'whether it occurred' statement is deliberately insufficient.
        if (
            at
            and first_time
            and at >= first_time
            and re.search(
                r"\b(?:follow.up completed|completed specialist review|"
                r"repeat (?:testing|test) (?:was )?completed)\b",
                text,
                re.I,
            )
            and not re.search(r"\b(?:no|not|if|whether|reported|outside|external)\b", text, re.I)
        ):
            completed.append(row)
    patient = values[0].data.get("patient_id")
    encounters = {r.data.get("encounter_id") for r in values} - {None}
    for row in rows:
        if (
            row.source.type == "referral"
            and row.data.get("patient_id") == patient
            and row.data.get("encounter_id") in encounters
        ):
            decisive.append(anchor(row, "status"))
            at = instant(row.data.get("appointment_at"))
            if row.data.get("status") == "completed" and at and first_time and at >= first_time:
                completed.append(row)
    # More than twenty contextual assertions is an explicit evidence budget boundary.
    if len(decisive) > 20:
        complete = False
    decisive = decisive[:20]
    state: Literal["documented", "not_documented", "unknown"] = (
        "documented" if completed else "not_documented" if complete else "unknown"
    )
    measurement_evidence = [
        Measurement(
            value=anchor(r, "value_numeric"), context={k: r.data.get(k) for k in CONTEXT_FIELDS}
        )
        for r in values
    ]
    citations = [m.value for m in measurement_evidence][:10]
    # Keep earliest/latest context and source documents visible, not only alphabetic first hits.
    context = list({a.model_dump_json(): a for a in decisive}.values())
    citations += context[:8]
    for row in rows:
        if row.source.type == "encounter" and row.source.id in encounters and len(citations) < 20:
            citations.append(anchor(row, "started_at"))
    name = str(values[0].data["test_name"])
    normal = sum(not abnormal(r) for r in values)
    claim = (
        f"{name}: {len(values)} source measurements across {len(encounters)} encounters, "
        f"{sum(abnormal(r) for r in values)} outside their own recorded reference bounds; "
        f"{normal} intermediate/other measurements within available bounds or without bounds. "
        f"Collection span {values[0].data['specimen_collected_at']} to "
        f"{values[-1].data['specimen_collected_at']}. "
    )
    claim += f"{len(recommendations)} related records document testing/follow-up plans. "
    claim += (
        "Linked follow-up completion is documented; this does not prove every action completed. "
        if completed
        else "No explicit completed follow-up was found in accessible searched records. "
        if complete
        else "Follow-up completion remains unknown because search/evidence is bounded. "
    )
    if last_time and first_time and last_time > first_time:
        claim += (
            "Later measurements exist; their relationship to every recommendation "
            "is unestablished. "
        )
    claim += (
        "Missing documentation does not prove missed care. "
        "Measurements do not establish diabetes or another diagnosis."
    )
    stop: Literal["budget_exhausted", "evidence_sufficient", "evidence_unavailable"] = (
        "budget_exhausted"
        if not complete
        else "evidence_sufficient"
        if completed
        else "evidence_unavailable"
    )
    return Candidate(
        type="clinical_relationship",
        rule="longitudinal_followup",
        title=f"Laboratory trend and follow-up: {name}",
        claim=claim,
        claim_kind="observation",
        anchors=citations,
        longitudinal=LongitudinalEvidence(
            group=key,
            measurements=measurement_evidence,
            search=manifest(rows),
            search_complete=complete,
            followup=decisive,
            followup_state=state,
            question=f"Do accessible records document follow-up of repeated {name} abnormalities?",
            stop_reason=stop,
        ),
        limitations=LIMITATIONS,
    )


def consolidate(candidates: list[Candidate]) -> list[Candidate]:
    covered = {
        m.value.source.id for c in candidates if c.longitudinal for m in c.longitudinal.measurements
    }
    result = []
    seen = set()
    for item in candidates:
        if item.rule in {"lab_change", "record_series"} and item.type == "laboratory_change":
            ids = {a.source.id for a in item.anchors if a.source.type == "observation"}
            if ids and ids <= covered:
                continue
        key = (
            "longitudinal:" + item.longitudinal.group
            if item.longitudinal
            else digest(item.model_dump(mode="json"))
        )
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result
