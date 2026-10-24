"""Deterministic plans and approval policy, independent of execution/persistence."""

from uuid import uuid4

from app.core.config import Settings
from app.core.provenance import digest
from app.schemas.investigation import SourceRecord
from app.schemas.planning import InvestigationContext, InvestigationTask, InvestigativeLead
from app.tools.inputs import INPUT_MODELS
from app.tools.registry import PERMISSIONS

TASK_AGENTS = {
    "discovery": "retrieval",
    "timeline": "timeline",
    "laboratory": "laboratory",
    "medication": "medication",
    "referrals": "contradiction",
}


def task(
    context: InvestigationContext, kind: str, reason: str, dependencies: list[str] | None = None
) -> InvestigationTask:
    return InvestigationTask(
        id=f"TASK-{uuid4().hex}",
        investigation_id=context.investigation_id,
        patient_id=context.patient_id,
        task_type=kind,  # type: ignore[arg-type]
        assigned_agent=TASK_AGENTS[kind],
        objective=context.objective,
        reason=reason,
        dependencies=dependencies or [],
        required_evidence=[kind],
    )


def initial_plan(context: InvestigationContext, discovery: str) -> list[InvestigationTask]:
    available = {r.type for r in context.manifest}
    full = context.objective in {"full_record_investigation", "hypothesis_investigation"}
    choices = []
    if full or context.objective in {"timeline_investigation", "contradiction_investigation"}:
        if available & {"encounter", "document"}:
            choices.append("timeline")
    if "observation" in available and (
        full
        or context.objective
        in {"laboratory_investigation", "medication_investigation", "followup_investigation"}
    ):
        choices.append("laboratory")
    if "medication" in available and (full or context.objective == "medication_investigation"):
        choices.append("medication")
    # Referrals aren't in the historical discovery manifest; the authorized check
    # discovers whether this modality exists, rather than assuming that it does.
    if full or context.objective in {"contradiction_investigation", "followup_investigation"}:
        choices.append("referrals")
    return [
        task(context, kind, f"Review available {kind} evidence for the objective.", [discovery])
        for kind in choices
    ]


def fingerprint(lead: InvestigativeLead, patient_id: str | None = None) -> str:
    # Originator/wording are deliberately excluded: two specialists may ask the same question.
    return digest(
        {
            "actions": sorted(
                [
                    {
                        "tool": action.tool,
                        "arguments": INPUT_MODELS[action.tool]
                        .model_validate(
                            {
                                "patient_id": patient_id,
                                **action.arguments,
                            }
                        )
                        .model_dump(mode="json"),
                    }
                    if patient_id
                    else action.model_dump(mode="json")
                    for action in lead.actions
                ],
                key=str,
            ),
            "sources": sorted([s.model_dump() for s in lead.sources], key=str),
        }
    )


def approve(
    lead: InvestigativeLead,
    context: InvestigationContext,
    records: dict[tuple[str, str], SourceRecord],
    settings: Settings,
    seen: set[str],
) -> tuple[InvestigationTask | None, str]:
    if lead.task_type != "followup":
        return None, "UNSUPPORTED_TASK_TYPE"
    parents = {t.id: t for t in context.tasks}
    parent = parents.get(lead.originating_task)
    if parent is None or parent.status != "completed" or parent.assigned_agent != lead.source_agent:
        return None, "INVALID_HANDOFF"
    if parent.depth >= settings.investigation_max_depth:
        return None, "DEPTH_BUDGET_EXHAUSTED"
    if len(context.tasks) >= settings.investigation_max_tasks:
        return None, "TASK_BUDGET_EXHAUSTED"
    if lead.assigned_agent not in PERMISSIONS or lead.assigned_agent == "synthesis":
        return None, "UNKNOWN_SPECIALIST"
    associated_ids: set[str] = set()
    for source in lead.sources:
        record = records.get((source.type, source.id))
        if (
            record is None
            or record.source_version != source.version
            or record.source_hash != source.hash
        ):
            return None, "UNKNOWN_OR_STALE_SOURCE"
        if record.data.get("patient_id", context.patient_id) != context.patient_id:
            return None, "PATIENT_SCOPE_VIOLATION"
        associated_ids.add(record.source.id)
        associated_ids.update(
            str(record.data[k])
            for k in ("encounter_id", "source_document_id")
            if record.data.get(k)
        )
    for action in lead.actions:
        if action.tool not in PERMISSIONS[lead.assigned_agent]:
            return None, "TOOL_NOT_PERMITTED"
        try:
            args = INPUT_MODELS[action.tool].model_validate(
                {
                    "patient_id": context.patient_id,
                    **action.arguments,
                }
            )
        except ValueError:
            return None, "INVALID_FILTERS"
        if args.patient_id != context.patient_id:
            return None, "PATIENT_SCOPE_VIOLATION"
        # Only implemented, narrow follow-ups; model/document text cannot widen the catalog.
        if action.tool == "search_documents":
            encounter = action.arguments.get("encounter_id")
            if not (
                (encounter in associated_ids and encounter is not None)
                or action.arguments.get("query") == "correction"
            ):
                return None, "UNSUPPORTED_RETRIEVAL_PURPOSE"
        elif action.tool in {"get_document", "get_encounter", "get_lab_result"}:
            if getattr(args, "record_id", None) not in associated_ids:
                return None, "UNRELATED_SOURCE_REQUEST"
        else:
            return None, "UNSUPPORTED_FOLLOWUP_TOOL"
    key = fingerprint(lead, context.patient_id)
    if key in seen:
        return None, "DUPLICATE_LEAD"
    seen.add(key)
    return InvestigationTask(
        id=f"TASK-{uuid4().hex}",
        investigation_id=context.investigation_id,
        patient_id=context.patient_id,
        task_type="followup",
        assigned_agent=lead.assigned_agent,
        objective=lead.question,
        reason=lead.reason,
        dependencies=[parent.id],
        parent_task=parent.id,
        lead_id=lead.id,
        sources=lead.sources,
        actions=lead.actions,
        depth=parent.depth + 1,
        priority=lead.priority,
        max_attempts=settings.investigation_task_attempts,
        max_tool_calls=settings.investigation_max_calls_per_agent,
        required_evidence=[lead.missing_information],
    ), "APPROVED"
