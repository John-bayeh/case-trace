"""Hospital HTTP adapters. Queries and projections belong to the service."""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, field_validator

from app.api.dependencies import asset_service, clinical_service
from app.hospital import schemas as dto
from app.hospital.asset_service import AssetDescriptor, ClinicalAssetService
from app.hospital.catalog import CaseCatalog, CaseOverview
from app.hospital.errors import HospitalError
from app.hospital.service import RESOURCES, ClinicalRecordService

router = APIRouter(prefix="/api/hospital/v1", tags=["hospital"])


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Query(20, ge=1, le=100)
    offset: int = Query(0, ge=0)
    start_at: datetime | None = None
    end_at: datetime | None = None
    encounter_id: str | None = None
    encounter_type: str | None = None
    department: str | None = None
    status: str | None = None
    test_code: str | None = None
    test_name: str | None = None
    medication_name: str | None = None
    document_type: str | None = None
    q: str | None = Query(default=None, min_length=1, max_length=200)
    event_type: str | None = None
    event_types: str | None = None
    sort: Literal["asc", "desc"] = "asc"

    @field_validator("start_at", "end_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("filter instants require explicit timezone")
        return value


Service = Annotated[ClinicalRecordService, Depends(clinical_service)]
Assets = Annotated[ClinicalAssetService, Depends(asset_service)]


def meta(request: Request) -> dto.Meta:
    return dto.Meta(request_id=request.state.request_id)


def collection(
    request: Request, data: list[Any], total: int, limit: int, offset: int
) -> dict[str, Any]:
    return {
        "data": data,
        "pagination": dto.Pagination(
            limit=limit, offset=offset, total=total, has_more=offset + len(data) < total
        ),
        "meta": meta(request),
    }


@router.get("/cases", response_model=dto.CollectionResponse[CaseOverview])
async def cases(
    request: Request,
    svc: Service,
    case_id: dto.Identifier | None = None,
    status: str | None = None,
    modality: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    items = await CaseCatalog(svc, request.app.state.settings).items(case_id)
    items = [
        item
        for item in items
        if (not status or item.status == status) and (not modality or modality in item.modalities)
    ]
    return collection(request, items[offset : offset + limit], len(items), limit, offset)


@router.get("/cases/{case_id}", response_model=dto.ResourceResponse[CaseOverview])
async def case_overview(case_id: dto.Identifier, request: Request, svc: Service) -> dict[str, Any]:
    items = await CaseCatalog(svc, request.app.state.settings).items(case_id)
    if not items:
        raise HospitalError()
    return {"data": items[0], "meta": meta(request)}


@router.get("/patients", response_model=dto.CollectionResponse[dto.PatientResponse])
async def patients(
    request: Request,
    svc: Service,
    query: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    data, total = await svc.patients(query, limit, offset)
    return collection(request, data, total, limit, offset)


@router.get("/patients/{patient_id}", response_model=dto.ResourceResponse[dto.PatientResponse])
async def patient(patient_id: str, request: Request, svc: Service) -> dict[str, Any]:
    return {"data": await svc.patient_dto(await svc.patient(patient_id)), "meta": meta(request)}


@router.get(
    "/patients/{patient_id}/summary", response_model=dto.ResourceResponse[dto.PatientSummary]
)
async def summary(patient_id: str, request: Request, svc: Service) -> dict[str, Any]:
    return {"data": await svc.summary(patient_id), "meta": meta(request)}


@router.get(
    "/patients/{patient_id}/timeline", response_model=dto.CollectionResponse[dto.TimelineEntry]
)
async def timeline(
    patient_id: str, request: Request, svc: Service, filters: Annotated[Filters, Query()]
) -> dict[str, Any]:
    data, total = await svc.timeline(patient_id, filters.model_dump())
    return collection(request, data, total, filters.limit, filters.offset)


@router.get(
    "/encounters/{encounter_id}/records", response_model=dto.ResourceResponse[dto.EncounterRecords]
)
async def encounter_records(encounter_id: str, request: Request, svc: Service) -> dict[str, Any]:
    return {"data": await svc.encounter_records(encounter_id), "meta": meta(request)}


class SeriesFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_code: str = Query(min_length=1)
    start_at: datetime | None = None
    end_at: datetime | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return Filters.aware(value)


@router.get(
    "/patients/{patient_id}/observations/series", response_model=dto.ResourceResponse[dto.LabSeries]
)
async def lab_series(
    patient_id: str, request: Request, svc: Service, filters: Annotated[SeriesFilters, Query()]
) -> dict[str, Any]:
    return {
        "data": await svc.lab_series(patient_id, filters.test_code, filters.model_dump()),
        "meta": meta(request),
    }


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str = Query(min_length=1, max_length=200)
    document_type: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = Query(20, ge=1, le=100)
    offset: int = Query(0, ge=0)

    @field_validator("start_at", "end_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        return Filters.aware(value)


@router.get(
    "/patients/{patient_id}/documents/search",
    response_model=dto.CollectionResponse[dto.DocumentSearchHit],
)
async def search_documents(
    patient_id: str, request: Request, svc: Service, filters: Annotated[SearchFilters, Query()]
) -> dict[str, Any]:
    data, total = await svc.search_documents(patient_id, filters.q, filters.model_dump())
    return collection(request, data, total, filters.limit, filters.offset)


def register(resource: str, schema: type[BaseModel]) -> None:
    async def listing(
        patient_id: str, request: Request, svc: Service, filters: Annotated[Filters, Query()]
    ) -> dict[str, Any]:
        data, total = await svc.list_records(resource, patient_id, filters.model_dump())
        return collection(request, data, total, filters.limit, filters.offset)

    async def detail(record_id: str, request: Request, svc: Service) -> dict[str, Any]:
        return {"data": await svc.get(resource, record_id), "meta": meta(request)}

    listing.__name__ = f"list_{resource.replace('-', '_')}"
    detail.__name__ = f"get_{resource.replace('-', '_')}"
    router.add_api_route(
        f"/patients/{{patient_id}}/{resource}",
        listing,
        response_model=dto.CollectionResponse.__class_getitem__(schema),
    )
    router.add_api_route(
        f"/{resource}/{{record_id}}",
        detail,
        response_model=dto.ResourceResponse.__class_getitem__(schema),
    )


for resource, (schema, _model, _time_field) in RESOURCES.items():
    register(resource, schema)


async def asset_response(request: Request, asset: AssetDescriptor) -> FileResponse:
    path = await request.app.state.asset_reader.verified_path(asset)
    return FileResponse(
        path,
        media_type=asset.mime_type,
        filename=f"{asset.external_id}{path.suffix}",
        content_disposition_type="attachment" if asset.mime_type == "text/html" else "inline",
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )


@router.get("/documents/{document_id}/asset", response_class=FileResponse)
async def document_asset(document_id: str, request: Request, assets: Assets) -> FileResponse:
    asset = await assets.document(document_id)
    return await asset_response(request, asset)


@router.get(
    "/imaging-studies/{study_id}/assets",
    response_model=dto.CollectionResponse[dto.ImagingAssetResponse],
)
async def imaging_assets(
    study_id: str,
    request: Request,
    assets: Assets,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    data, total = await assets.images(study_id, limit, offset)
    return collection(request, data, total, limit, offset)


@router.get("/imaging-assets/{asset_id}/content", response_class=FileResponse)
async def imaging_content(asset_id: str, request: Request, assets: Assets) -> FileResponse:
    asset = await assets.imaging(asset_id)
    return await asset_response(request, asset)


@router.get(
    "/imaging-studies/{study_id}/report", response_model=dto.ResourceResponse[dto.DocumentResponse]
)
async def imaging_report(study_id: str, request: Request, svc: Service) -> dict[str, Any]:
    return {"data": await svc.imaging_report(study_id), "meta": meta(request)}
