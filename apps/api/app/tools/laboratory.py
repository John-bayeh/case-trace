"""Deterministic comparison; no conversion, diagnosis or significance inference."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.hospital.errors import HospitalError
from app.schemas.investigation import LabComparison, SourceRef, ToolResult
from app.tools.inputs import ComparisonInput, LabInput
from app.tools.results import result_for

if TYPE_CHECKING:
    from app.tools.clinical import ClinicalTools


async def compare(clinical: "ClinicalTools", args: ComparisonInput) -> ToolResult:
    if args.record_id and args.other_id:
        records = [
            await clinical.resolve(args.patient_id, SourceRef(type="observation", id=id_))
            for id_ in (args.record_id, args.other_id)
        ]
    else:
        records = []
        offset = 0
        while True:
            page = await clinical.list_records(
                "observation",
                LabInput(
                    patient_id=args.patient_id,
                    test_name=args.test_name,
                    test_code=args.test_code,
                    limit=100,
                    offset=offset,
                ),
            )
            records.extend(page.records)
            if not page.has_more:
                break
            offset += len(page.records)
            if not page.records or offset > 10000:
                raise HospitalError("COMPARISON_SELECTION_TOO_LARGE", 409)
        if len(records) < 2:
            raise HospitalError("INSUFFICIENT_OBSERVATIONS", 422)
    codes = [r.data.get("test_code") for r in records]
    compatible = (
        len(set(codes)) == 1
        if all(codes)
        else (not any(codes) and len({r.data["test_name"].casefold() for r in records}) == 1)
    )
    units = {r.data.get("unit") for r in records}
    if not compatible or len(units) != 1 or None in units or "" in units:
        raise HospitalError("INCOMPARABLE_OBSERVATIONS", 422)
    if any(r.data.get("value_numeric") is None for r in records):
        raise HospitalError("NON_NUMERIC_OBSERVATIONS", 422)
    if any(r.data.get("specimen_collected_at") is None for r in records):
        raise HospitalError("UNKNOWN_COLLECTION_TIME", 422)
    records.sort(
        key=lambda r: (datetime.fromisoformat(r.data["specimen_collected_at"]), r.source.id)
    )
    records = [records[0], records[-1]]
    before, after = [Decimal(str(r.data["value_numeric"])) for r in records]
    change = after - before
    result = result_for(records, 2)
    result.analysis = LabComparison(
        direction="increasing" if change > 0 else "decreasing" if change < 0 else "unchanged",
        change_absolute=float(change),
        change_percent=float(change / before * 100) if before != 0 else None,
    )
    return result
