"""Search projections explicitly retain the original source fingerprint."""

from typing import TYPE_CHECKING

from app.core.provenance import digest
from app.hospital.errors import HospitalError
from app.schemas.investigation import SourceRef, ToolResult
from app.tools.inputs import DocumentSearchInput
from app.tools.results import result_for

if TYPE_CHECKING:
    from app.tools.clinical import ClinicalTools


async def search(clinical: "ClinicalTools", args: DocumentSearchInput) -> ToolResult:
    if args.encounter_id:
        await clinical.resolve(args.patient_id, SourceRef(type="encounter", id=args.encounter_id))
    hits, total = await clinical.source.search_documents(
        args.patient_id,
        args.query,
        args.model_dump(exclude_none=True, exclude={"patient_id", "query"}),
    )
    records = []
    for hit in hits:
        record = await clinical.resolve(args.patient_id, SourceRef(type="document", id=hit.id))
        data = record.data
        hit_data = hit.model_dump(mode="json")
        if (
            any(hit_data[key] != data[key] for key in ("id", "title", "document_type", "event_at"))
            or (args.encounter_id and data.get("encounter_id") != args.encounter_id)
            or (args.document_type and data.get("document_type") != args.document_type)
            or (args.department and data.get("metadata", {}).get("department") != args.department)
            or hit.snippet not in (data.get("text_content") or "")
        ):
            raise HospitalError("INVALID_SEARCH_RESULT", 422)
        # Never mutate a source owned by an injected adapter.
        record = record.model_copy(deep=True)
        record.data = hit_data
        record.representation = "search_hit"
        record.representation_hash = digest(record.data)
        records.append(record)
    return result_for(records, total, args.offset)
