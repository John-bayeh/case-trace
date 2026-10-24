"""Clinical tool handlers over injected DTO capabilities."""

from pydantic import BaseModel

from app.clinical.ports import ClinicalSource
from app.hospital.errors import HospitalError
from app.schemas.investigation import SourceRecord, SourceRef, SourceType, ToolResult
from app.tools.inputs import INPUT_MODELS, PageInput, PatientInput
from app.tools.results import result_for as result_for
from app.tools.results import validate_source


class ClinicalTools:
    def __init__(self, source: ClinicalSource):
        self.source = source

    async def resolve(self, patient_id: str, source: SourceRef) -> SourceRecord:
        record = await self.source.resolve(patient_id, source)
        if record.source != source:
            raise HospitalError("INVALID_SOURCE_PROVENANCE", 422)
        validate_source(record, patient_id)
        # Imaging assets derive ownership from the independently scoped parent study.
        if source.type == "imaging_asset":
            await self.resolve(
                patient_id, SourceRef(type="imaging_study", id=record.data["imaging_study_id"])
            )
        return record

    async def list_records(self, source_type: SourceType, args: PageInput) -> ToolResult:
        filters = args.model_dump(exclude_none=True, exclude={"patient_id"})
        encounter = filters.get("encounter_id")
        if encounter:
            await self.resolve(args.patient_id, SourceRef(type="encounter", id=encounter))
        if source_type == "referral" and "department" in filters:
            filters["referred_department"] = filters.pop("department")
        if source_type == "imaging_study" and "imaging_study_id" in filters:
            filters["id"] = filters.pop("imaging_study_id")
        if source_type == "diagnostic_report" and filters.get("imaging_study_id"):
            await self.resolve(
                args.patient_id, SourceRef(type="imaging_study", id=filters["imaging_study_id"])
            )
        if source_type == "encounter":
            filters["_sort"] = "asc"
        filters["_casefold"] = True
        if source_type == "medication":
            filters["_time_field"] = "ordered_at"
        records, total = await self.source.records(source_type, args.patient_id, filters)
        for record in records:
            validate_source(record, args.patient_id)
            if record.source.type != source_type:
                raise HospitalError("INVALID_SOURCE_PROVENANCE", 422)
        return result_for(records, total, args.offset)


# name -> source type, operation. Descriptions and schemas are exposed by the registry.
TOOL_SPECS: dict[str, tuple[SourceType, str]] = {
    "get_patient": ("patient", "get"),
    "search_patient": ("patient", "patient_search"),
    "get_encounters": ("encounter", "list"),
    "get_encounter": ("encounter", "get"),
    "build_patient_timeline": ("clinical_event", "timeline"),
    "search_clinical_notes": ("document", "search"),
    "get_clinical_note": ("document", "get"),
    "search_documents": ("document", "search"),
    "get_document": ("document", "get"),
    "get_lab_results": ("observation", "list"),
    "get_lab_result": ("observation", "get"),
    "compare_lab_results": ("observation", "compare"),
    "get_medication_history": ("medication", "list"),
    "get_medication": ("medication", "get"),
    "get_diagnostic_reports": ("diagnostic_report", "list"),
    "get_diagnostic_report": ("diagnostic_report", "get"),
    "get_imaging_studies": ("imaging_study", "list"),
    "get_imaging_asset_metadata": ("imaging_asset", "get"),
    "get_imaging_report": ("document", "imaging_report"),
    "get_referrals": ("referral", "list"),
}


async def dispatch(clinical: ClinicalTools, name: str, args: BaseModel) -> ToolResult:
    # Also validate legacy direct Python callers; defaults are not supplied filters.
    parsed = INPUT_MODELS[name].model_validate(args.model_dump(exclude_unset=True))
    return await execute_handler(clinical, name, parsed)


async def execute_handler(clinical: ClinicalTools, name: str, args: PatientInput) -> ToolResult:
    from app.tools.documents import search
    from app.tools.inputs import ComparisonInput, DocumentSearchInput, TimelineInput
    from app.tools.laboratory import compare
    from app.tools.timeline import build_timeline

    kind, operation = TOOL_SPECS[name]
    if operation == "list":
        assert isinstance(args, PageInput)
        return await clinical.list_records(kind, args)
    if operation == "search":
        assert isinstance(args, DocumentSearchInput)
        return await search(clinical, args)
    if operation == "compare":
        assert isinstance(args, ComparisonInput)
        return await compare(clinical, args)
    if operation == "timeline":
        assert isinstance(args, TimelineInput)
        return await build_timeline(clinical, args)
    identifier = getattr(args, "record_id", args.patient_id)
    if operation == "imaging_report":
        study = await clinical.resolve(
            args.patient_id, SourceRef(type="imaging_study", id=identifier)
        )
        identifier = study.data.get("report_document_id")
        if not identifier:
            raise HospitalError("IMAGING_REPORT_NOT_FOUND", 404)
    record = await clinical.resolve(args.patient_id, SourceRef(type=kind, id=identifier))
    encounter = getattr(args, "encounter_id", None)
    if encounter:
        await clinical.resolve(args.patient_id, SourceRef(type="encounter", id=encounter))
        association = record.data.get("encounter_id")
        if kind == "imaging_asset":
            parent = await clinical.resolve(
                args.patient_id, SourceRef(type="imaging_study", id=record.data["imaging_study_id"])
            )
            association = parent.data.get("encounter_id")
        if association != encounter:
            raise HospitalError("ENCOUNTER_SCOPE_VIOLATION", 403)
    if getattr(args, "source_version", None) not in (None, record.source_version) or getattr(
        args, "source_hash", None
    ) not in (None, record.source_hash):
        raise HospitalError("STALE_SOURCE_REFERENCE", 409)
    if operation == "patient_search":
        query = str(getattr(args, "query", "")).strip().casefold()
        fields = ("id", "synthetic_identifier", "display_name")
        if query and not any(query in record.data[key].casefold() for key in fields):
            return result_for([], 0)
    return result_for([record], 1)
