"""Explicit permissions, patient scope, budgets, audit and bounded tool execution."""

import asyncio
from typing import Any
from uuid import UUID

from app.core.provenance import digest
from app.hospital.errors import HospitalError
from app.orchestration.ports import ToolAudit
from app.schemas.investigation import ToolResult
from app.tools.clinical import TOOL_SPECS, ClinicalTools, dispatch
from app.tools.inputs import INPUT_MODELS, PageInput
from app.tools.results import validate_result

PERMISSIONS = {
    "retrieval": {
        "get_patient",
        "search_patient",
        "get_encounters",
        "search_documents",
        "get_lab_results",
        "get_medication_history",
        "get_imaging_studies",
        "get_imaging_asset_metadata",
        "get_diagnostic_reports",
    },
    "timeline": {
        "get_encounters",
        "get_encounter",
        "build_patient_timeline",
        "search_clinical_notes",
        "search_documents",
        "get_document",
        "get_clinical_note",
        "get_lab_results",
        "get_medication_history",
    },
    "laboratory": {
        "get_encounters",
        "get_encounter",
        "get_referrals",
        "get_lab_results",
        "get_lab_result",
        "compare_lab_results",
        "search_documents",
        "get_document",
    },
    "medication": {"get_medication_history", "get_medication", "search_documents", "get_document"},
    "contradiction": {
        "get_encounters",
        "get_encounter",
        "search_documents",
        "get_document",
        "get_clinical_note",
        "get_lab_results",
        "get_lab_result",
        "get_diagnostic_reports",
        "get_diagnostic_report",
        "get_imaging_studies",
        "get_imaging_report",
        "get_referrals",
    },
    "synthesis": set(),
}

# Aggregation cannot turn one permitted tool into unrestricted clinical access.
TIMELINE_READS = {
    "events": "build_patient_timeline",
    "encounters": "get_encounters",
    "documents": "get_document",
    "observations": "get_lab_results",
    "medications": "get_medication_history",
    "imaging_studies": "get_imaging_studies",
    "diagnostic_reports": "get_diagnostic_reports",
    "referrals": "get_referrals",
}

DESCRIPTIONS = {
    "get_patient": "Retrieve the selected synthetic patient's demographics.",
    "search_patient": "Match ID, synthetic MRN or name within the selected patient only.",
    "get_encounters": "List encounters chronologically with period, department and type filters.",
    "get_encounter": "Retrieve one exact encounter.",
    "search_clinical_notes": "Search document text by case-insensitive substring and metadata.",
    "get_clinical_note": "Retrieve an original document, including clinical text and named times.",
    "search_documents": "Search titles/text; return snippets and original source fingerprints.",
    "get_document": "Retrieve original document text and metadata; verify its registered asset.",
    "get_lab_results": "List observations by analyte, encounter, status and collection period.",
    "get_lab_result": "Retrieve values, units and collection/report times for one observation.",
    "compare_lab_results": (
        "Compare a numeric pair or an analyte's earliest/latest results; "
        "no clinical significance is inferred."
    ),
    "get_medication_history": (
        "List medications by name, encounter, status and order period; "
        "no administration is inferred."
    ),
    "get_medication": "Retrieve one exact medication record with source-document association.",
    "get_diagnostic_reports": "List diagnostic reports by type, encounter, study and issue period.",
    "get_diagnostic_report": "Retrieve one exact diagnostic report and its recorded source links.",
    "get_imaging_studies": "Filter studies by ID, modality, body region, encounter and period.",
    "get_imaging_asset_metadata": "Retrieve illustrative image metadata; never interprets pixels.",
    "get_imaging_report": "Retrieve the original report document linked to an exact imaging study.",
    "get_referrals": "Filter referrals by status, receiving department, encounter and order time.",
    "build_patient_timeline": (
        "Aggregate authorized source categories and named chronology; defaults to clinical events."
    ),
}


class ToolRegistry:
    def __init__(
        self,
        store: ToolAudit,
        clinical: ClinicalTools,
        public_id: str,
        patient_id: str,
        *,
        max_calls: int = 100,
        max_per_agent: int = 30,
        timeout: float = 15,
        max_chars: int = 100000,
    ):
        self.store, self.clinical = store, clinical
        self.public_id, self.patient_id = public_id, patient_id
        self.max_calls, self.max_per_agent = max_calls, max_per_agent
        self.timeout, self.max_chars = timeout, max_chars
        self.calls = 0
        self.agent_calls: dict[str, int] = {}

    def catalog(self, agent: str) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "description": DESCRIPTIONS[name],
                "input_schema": INPUT_MODELS[name].model_json_schema(),
                "output_schema": ToolResult.model_json_schema(),
                "scope": f"{TOOL_SPECS[name][0]}.read",
                **(
                    {
                        "allowed_categories": [
                            category
                            for category, tool in TIMELINE_READS.items()
                            if tool in PERMISSIONS.get(agent, set())
                        ]
                    }
                    if name == "build_patient_timeline"
                    else {}
                ),
            }
            for name in sorted(PERMISSIONS.get(agent, set()))
        ]

    async def execute(
        self,
        agent: str,
        agent_id: UUID,
        name: str,
        raw: dict[str, Any],
    ) -> ToolResult:
        # Never log arbitrary unvalidated payloads (which could contain secrets).
        call_id = await self.store.tool_start(
            self.public_id,
            agent_id,
            name[:100],
            {
                "patient_id": self.patient_id,
                "filter_fingerprint": digest(
                    {
                        key: str(value)[:200]
                        for key, value in raw.items()
                        if key in INPUT_MODELS.get(name, PageInput).model_fields
                    }
                ),
                **{
                    key: value
                    for key, value in raw.items()
                    if key
                    in {
                        "patient_id",
                        "record_id",
                        "other_id",
                        "limit",
                        "offset",
                        "encounter_id",
                        "document_id",
                        "observation_id",
                        "medication_id",
                        "report_id",
                        "imaging_study_id",
                        "imaging_asset_id",
                    }
                    and (
                        isinstance(value, int)
                        or isinstance(value, str)
                        and len(value) <= 100
                        and value.replace("-", "").replace("_", "").isalnum()
                    )
                },
            },
            agent,
        )
        try:
            if name not in PERMISSIONS.get(agent, set()) or name not in TOOL_SPECS:
                raise HospitalError("TOOL_NOT_PERMITTED", 403)
            args = INPUT_MODELS[name].model_validate({"patient_id": self.patient_id, **raw})
            if args.patient_id != self.patient_id:
                raise HospitalError("PATIENT_SCOPE_VIOLATION", 403)
            if name == "build_patient_timeline" and any(
                TIMELINE_READS.get(category) not in PERMISSIONS.get(agent, set())
                for category in getattr(args, "include", [])
            ):
                raise HospitalError("TOOL_NOT_PERMITTED", 403)
            # No await between testing and incrementing shared budgets.
            if self.calls >= self.max_calls or self.agent_calls.get(agent, 0) >= self.max_per_agent:
                raise HospitalError("TOOL_BUDGET_EXCEEDED", 409)
            self.calls += 1
            self.agent_calls[agent] = self.agent_calls.get(agent, 0) + 1
            async with asyncio.timeout(self.timeout):
                result = await dispatch(self.clinical, name, args)
                validate_result(result, self.patient_id)
                if isinstance(args, PageInput) and len(result.records) > args.limit:
                    raise HospitalError("INVALID_TOOL_RESULT", 422)
                if isinstance(args, PageInput) and (
                    result.has_more != (args.offset + len(result.records) < result.total)
                    or result.has_more
                    and not result.records
                ):
                    raise HospitalError("INVALID_TOOL_RESULT", 422)
            if len(result.model_dump_json()) > self.max_chars:
                raise HospitalError("TOOL_RESULT_TOO_LARGE", 409)
        except BaseException as exc:
            code = exc.code if isinstance(exc, HospitalError) else type(exc).__name__
            await self.store.tool_end(self.public_id, call_id, [], code)
            raise
        await self.store.tool_end(
            self.public_id, call_id, [ref.model_dump() for ref in result.source_refs]
        )
        await self.store.record(
            self.public_id,
            "tool.page",
            {
                "tool_execution_id": str(call_id),
                "record_count": len(result.records),
                "total": result.total,
                "has_more": result.has_more,
                "representations": sorted({r.representation for r in result.records}),
            },
        )
        return result
