# API Patterns (FastAPI)

## Router example
```py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/patients", tags=["patients"])

class PatientSummaryResponse(BaseModel):
    patient_id: str
    display_name: str

@router.get("/{patient_id}", response_model=PatientSummaryResponse)
async def get_patient(patient_id: str, service=Depends(get_patient_service)):
    patient = await service.get_summary(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientSummaryResponse.model_validate(patient)
```
`get_patient_service` is an application-provided dependency, not a ready-to-run import. Adapt paths and errors to the authoritative contract.

## Interface requirements
- Model every request and response with documented Pydantic schemas; never expose ORM entities directly.
- Match existing endpoint paths, pagination conventions, casing, enum values, and status codes.
- Validate patient, encounter, and investigation IDs at boundaries without assuming numeric identifiers.
- Use filtering and pagination for long encounter, lab, and event histories; define stable sort order.
- Use RFC 3339 timestamps with explicit offsets. Do not remove collection vs documentation timestamps.
- Use consistent `request_id` and safe machine-readable error codes according to contract.
- Protect write endpoints against duplicate submission with idempotency where specified.

## Agent tool API
Tool output should communicate `tool_call_id`, requested scope, actual retrieved record IDs, source provenance, execution status, and failure information. An empty successful query is different from an unavailable retrieval. Do not include ground-truth annotations in source-facing endpoints.

## API tests
Cover valid/invalid models, nonexistent IDs, filtering, pagination, timestamp serialization, access control if implemented, error envelope, duplicate invocation, and absence of hidden fixture answer keys.
