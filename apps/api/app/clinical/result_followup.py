"""Bounded source-led result reconciliation, independent of case IDs and diagnoses."""

import re

from app.clinical.claims import ClinicalClaim
from app.clinical.relationship_models import RelationshipEvidence
from app.clinical.result_models import (
    STAGES,
    ResultSearchScope,
    ResultWorkflow,
    StageName,
    WorkflowObservation,
    WorkflowSource,
    WorkflowStage,
    WorkflowState,
)
from app.clinical.rules import anchor, instant
from app.core.provenance import digest
from app.schemas.investigation import Candidate, SourceRecord

LIMITATIONS = [
    "Accessible records only; missing documentation does not prove an action never occurred.",
    "Administrative closure, routing and scheduled appointments do not prove clinical completion.",
    "Referral appointment fields are searched; standalone "
    "appointments and external records are unavailable.",
    "No recommended deadline is inferred; negligence, progression and "
    "diagnosis are not established.",
    "Document event/authoring times and literal narrative dates "
    "remain distinct; late entries may clarify care.",
]


def search_scope(rows: list[SourceRecord], complete: bool) -> ResultSearchScope:
    return ResultSearchScope(
        complete=complete,
        sources=[
            WorkflowSource(source=r.source, version=r.source_version, hash=r.source_hash)
            for r in sorted(rows, key=lambda r: (r.source.type, r.source.id))
        ],
    )


def actionable(row: SourceRecord) -> bool:
    text = str(row.data.get("conclusion") or "")
    return (
        row.source.type == "diagnostic_report"
        and row.data.get("status") in {"final", "finalized", "corrected", "amended"}
        and bool(
            re.search(
                r"\b(?:abnormal|actionable|requiring clinical follow.up|follow.up recommended|"
                r"recommend(?:ed|ation)?\s*:?\s*(?:review|follow.up))\b",
                text,
                re.I,
            )
        )
        and not bool(re.search(r"\b(?:no|not)\s+(?:abnormal|actionable)\b", text, re.I))
    )


def related(row: SourceRecord, report: SourceRecord, unique: bool) -> bool:
    if row.data.get("patient_id") != report.data.get("patient_id"):
        return False
    if row.source == report.source or row.source.id == report.data.get("document_id"):
        return True
    text = " ".join(str(row.data.get(k) or "") for k in ("title", "text_content", "reason"))
    if report.source.id in text:
        return True
    if row.source.type == "encounter":
        return row.source.id == report.data.get("encounter_id")
    if not unique:
        return False
    if report.data.get("encounter_id") and (
        row.data.get("encounter_id") == report.data.get("encounter_id")
    ):
        return True
    # Without an explicit accession link, multiple actionable reports are ambiguous.
    words = set(re.findall(r"[a-z]{4,}", str(report.data.get("title", "")).lower())) - {
        "report",
        "result",
        "final",
        "diagnostic",
        "test",
    }
    overlap = words & set(re.findall(r"[a-z]{4,}", text.lower()))
    return (
        len(overlap) >= 2
        or bool(
            overlap
            and re.search(
                r"\b(?:result|report|follow.up|referral|review|biopsy|specimen)\b", text, re.I
            )
        )
        or bool(
            re.search(r"\b(?:result|referral)\b", text, re.I)
            and re.search(
                r"\b(?:rout\w*|closed|acknowledged|patient communication|follow.up|unbooked)\b",
                text,
                re.I,
            )
        )
    )


def observations(row: SourceRecord) -> list[WorkflowObservation]:
    result: list[WorkflowObservation] = []

    def add(
        stage: StageName, state: WorkflowState, field: str, time_field: str | None = None
    ) -> None:
        value = str(row.data.get(field) or "")
        if len(value) > 2000:
            return
        literal = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", value)[:10]
        at = instant(row.data.get(time_field)) if time_field else None
        if (
            stage == "administrative_closure"
            and literal
            and at
            and any(d != at.date().isoformat() for d in literal)
        ):
            state = "conflicting"
        if (
            stage == "completed"
            and literal
            and at
            and any(d != at.date().isoformat() for d in literal)
        ):
            # A historical date in prose cannot be replaced by the note event time.
            time_field = None
        result.append(
            WorkflowObservation(
                stage=stage,
                state=state,
                anchor=anchor(row, field),
                event_time_field=time_field,
                timestamps={k: v for k, v in row.data.items() if k.endswith("_at")},
                literal_dates=literal,
            )
        )

    if row.source.type == "diagnostic_report":
        add("finalized", "documented", "status", "issued_at")
        return result
    if row.source.type == "referral":
        status = row.data.get("status")
        if status in {"scheduled", "completed"} and row.data.get("appointment_at"):
            add("scheduled", "documented", "status", "appointment_at")
        if status == "completed":
            add("completed", "documented", "status", "appointment_at")
        elif status in {"ordered", "scheduled", "unknown", "no_show", "cancelled"}:
            add("completed", "partial", "status", "ordered_at")
        return result
    if row.source.type != "document":
        return result
    text = str(row.data.get("text_content") or "")
    kind = str(row.data.get("document_type") or "")
    if kind in {"procedure_order", "test_order"}:
        add("ordered", "documented", "text_content", "event_at")
    if kind == "procedure_note" and re.search(r"\b(?:performed|biopsied|obtained)\b", text, re.I):
        add("performed", "documented", "text_content", "event_at")
    if kind == "specimen_record" and re.search(r"\bcollected\b", text, re.I):
        add("specimen_collected", "documented", "text_content", "event_at")
    patterns: list[tuple[StageName, WorkflowState, str]] = [
        ("routed", "documented", r"\bresult routed|\breport (?:routed|delivered)"),
        ("acknowledged", "documented", r"\b(?:result|report) acknowledged\b"),
        (
            "acknowledged",
            "unknown",
            r"\b(?:not acknowledged|acknowledg\w* (?:unknown|unverified))\b",
        ),
        (
            "patient_notification",
            "documented",
            r"\b(?:patient (?:was )?notified|patient given written instructions|"
            r"(?:result|report) discussed with patient|"
            r"discussed (?:the )?(?:pathology|result|report)[^.]{0,80}with (?:the )?patient)\b",
        ),
        (
            "patient_notification",
            "unknown",
            r"\b(?:no (?:linked telephone note|documentation|patient communication)|"
            r"does not document patient|cannot establish when|contact outcome is not documented)\b",
        ),
        (
            "recommended",
            "documented",
            r"\b(?:recommend(?:ation|s|ed)?\b[^.]{0,100}(?:review|follow.up)|"
            r"follow.up (?:is )?recommended)",
        ),
        ("scheduled", "documented", r"\b(?:follow.up|referral|appointment) scheduled\b"),
        ("scheduled", "partial", r"\b(?:unbooked|scheduling status pending|not scheduled)\b"),
        (
            "completed",
            "documented",
            r"\b(?:follow.up completed|completed specialist (?:review|appointment)|"
            r"(?:pathology|result|report) (?:is |was )?reviewed today)\b",
        ),
        (
            "completed",
            "partial",
            r"\b(?:no documentation|does not mention|no completed follow.up|not completed|"
            r"outside (?:the |current )?(?:records|system))\b",
        ),
        ("administrative_closure", "documented", r"\b(?:closed|administrative closure)\b"),
    ]
    for stage, state, pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        # Positive assertions cannot be supplied by negated or conditional language.
        if state == "documented" and re.search(
            r"\b(?:no|not|never|if|consider)\s+(?:\w+\s+){0,3}$", text[: match.start()], re.I
        ):
            continue
        if (
            stage == "completed"
            and state == "documented"
            and re.search(r"\b(?:patient reports?|outside|external|reportedly)\b", text, re.I)
        ):
            continue
        sentence_prefix = re.split(r"[.!?\n]", text[: match.start()])[-1]
        if state == "documented" and re.search(
            r"\b(?:no documentation|does not mention|not documented|hypothetical|if)\b",
            sentence_prefix,
            re.I,
        ):
            continue
        add(stage, state, "text_content", "event_at")
    return result


def result_relationships(rows: list[SourceRecord], scope: ResultSearchScope) -> list[Candidate]:
    reports = [r for r in rows if actionable(r)]
    candidates = []
    # Duplicate representations of one result document are one workflow.
    seen = set()
    for report in sorted(reports, key=lambda r: r.source.id)[:3]:
        identity = report.data.get("document_id") or report.source.id
        if identity in seen:
            continue
        seen.add(identity)
        unique = len({r.data.get("document_id") or r.source.id for r in reports}) == 1
        linked = [r for r in rows if related(r, report, unique)]
        # Follow the originating procedure's title back to a unique earlier order.
        # Do not attach every order in the chart or infer missing accession links.
        if unique:
            for procedure in list(linked):
                if procedure.data.get("document_type") != "procedure_note":
                    continue
                terms = set(
                    re.findall(r"[a-z]{4,}", str(procedure.data.get("title") or "").lower())
                ) - {"procedure", "note", "report", "order"}
                procedure_time = instant(procedure.data.get("event_at"))
                orders = [
                    r
                    for r in rows
                    if r.data.get("patient_id") == report.data.get("patient_id")
                    and r.data.get("document_type") in {"procedure_order", "test_order"}
                    and len(
                        terms
                        & set(re.findall(r"[a-z]{4,}", str(r.data.get("title") or "").lower()))
                    )
                    >= 2
                    and (order_time := instant(r.data.get("event_at")))
                    and procedure_time
                    and order_time <= procedure_time
                ]
                if len(orders) == 1 and orders[0] not in linked:
                    linked.append(orders[0])
        found = [o for r in linked for o in observations(r)]
        if not any(o.stage == "recommended" for o in found):
            continue
        if not any(
            o.stage in {"administrative_closure", "completed", "scheduled", "routed"} for o in found
        ):
            continue
        lifecycle = []
        for stage in STAGES:
            items = sorted(
                [o for o in found if o.stage == stage], key=lambda o: o.anchor.model_dump_json()
            )
            states = {o.state for o in items}
            state = (
                "unknown"
                if not items
                else "conflicting"
                if "conflicting" in states
                else ("partial" if len(states) > 1 or "partial" in states else items[0].state)
            )
            lifecycle.append(WorkflowStage(stage=stage, state=state, observations=items[:40]))
        # Select distinct original records for constituent assertions; the full
        # lifecycle and search retain all counterevidence, not just these anchors.
        priority: list[StageName] = [
            "finalized",
            "performed",
            "recommended",
            "routed",
            "administrative_closure",
            "completed",
            "patient_notification",
            "scheduled",
        ]
        selected: dict[tuple[str, str], WorkflowObservation] = {}
        for stage in priority:
            for o in sorted(
                [o for o in found if o.stage == stage], key=lambda o: o.anchor.source.id
            ):
                selected.setdefault((o.anchor.source.type, o.anchor.source.id), o)
        chosen = list(selected.values())[:8]
        if len(chosen) < 2:
            continue
        assertions = [
            ClinicalClaim(
                id="RF-" + digest(o.model_dump(mode="json"))[:24],
                patient_id=report.data.get("patient_id"),
                anchor=o.anchor,
                concept=report.source.id,
                original_concept=report.data.get("title", "Diagnostic result"),
                assertion="followup_status",
                value=f"{o.stage}:{o.state}",
                recorded_status=o.state,
                origin="clinician_record",
                timestamps=o.timestamps,
                event_time_field=o.event_time_field,
                documentation_time_field="authored_at"
                if o.anchor.source.type == "document"
                else None,
            )
            for o in chosen
        ]
        citations = [o.anchor for o in chosen]
        by_source = {(r.source.type, r.source.id): r for r in rows}
        for o in chosen:
            row = by_source[(o.anchor.source.type, o.anchor.source.id)]
            if o.event_time_field and row.data.get(o.event_time_field):
                citations.append(anchor(row, o.event_time_field))
        citations.append(anchor(report, "conclusion"))
        issued = str(report.data.get("issued_at") or "unknown")
        completed = [o for o in found if o.stage == "completed" and o.state == "documented"]
        result_time = instant(issued)
        dated_completion = [
            o
            for o in completed
            if result_time
            and (t := instant(o.timestamps.get(o.event_time_field or "")))
            and t >= result_time
        ]
        completion_times = sorted(
            {str(o.timestamps.get(o.event_time_field or "") or "unknown") for o in dated_completion}
        )
        partial = any(o.stage == "completed" and o.state == "partial" for o in found)
        closure = any(o.stage == "administrative_closure" for o in found)
        claim = (
            f"Finalized result {report.source.id} ({issued}) has a documented "
            "follow-up recommendation. "
        )
        if closure and partial:
            claim += (
                "Administrative closure and clinical follow-up documentation "
                "disagree: interim records leave completion unverified. "
            )
        elif partial:
            claim += "Follow-up completion remains partially documented. "
        if dated_completion:
            claim += (
                "Later/current completed review is documented at "
                + ", ".join(completion_times[:3])
                + "; this does not establish earlier communication or completion of "
                "every recommended action. "
            )
        elif completed:
            claim += (
                "Completion is recorded but its timing relative to the result remains uncertain. "
            )
        else:
            claim += "No completed follow-up is documented in the accessible searched records. "
        if any(o.stage == "patient_notification" and o.state == "documented" for o in found):
            claim += "Patient notification is documented; its first occurrence remains uncertain. "
        else:
            claim += "Patient communication remains unverified. "
        claim += "Missing documentation does not prove non-occurrence."
        workflow = ResultWorkflow(
            result_id=report.source.id,
            search=scope,
            lifecycle=lifecycle,
            attribution="unique_result_context" if unique else "explicit_link",
        )
        candidates.append(
            Candidate(
                type="clinical_relationship",
                title="Diagnostic result and follow-up reconciliation",
                claim=claim,
                claim_kind="observation",
                rule="clinical_relationship",
                anchors=list({a.model_dump_json(): a for a in citations}.values()),
                relationship=RelationshipEvidence(
                    relationship_type="result_followup",
                    assertions=assertions,
                    supporting_assertion_ids=[a.id for a in assertions],
                    result_workflow=workflow,
                    unresolved_questions=[
                        "When was the patient first informed?",
                        "Were other recommended actions completed outside accessible records?",
                    ],
                ),
                limitations=LIMITATIONS,
                alternatives=[
                    "External care, undocumented communication or late documentation "
                    "may explain gaps."
                ],
            )
        )
    return candidates
