"""Typed hospital projections and clinical chronology, without investigation inference."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel

from app.hospital import schemas as dto
from app.hospital.errors import HospitalError as HospitalError
from app.hospital.repository import HospitalRepository
from app.models import hospital as db

# Canonical DTO, persistence model, and clinical sort field.
RESOURCES: dict[str, tuple[type[BaseModel], type[Any], str]] = {
    "diagnoses": (dto.Diagnosis, db.Diagnosis, "diagnosed_at"),
    "symptoms": (dto.Symptom, db.Symptom, "onset_at"),
    "diagnostic-reports": (dto.DiagnosticReport, db.DiagnosticReport, "issued_at"),
    "encounters": (dto.Encounter, db.Encounter, "started_at"),
    "clinical-events": (dto.ClinicalEvent, db.ClinicalEvent, "occurred_at"),
    "observations": (dto.Observation, db.LabResult, "specimen_collected_at"),
    "medications": (dto.Medication, db.MedicationEvent, "start_at"),
    "documents": (dto.DocumentResponse, db.ClinicalDocument, "event_at"),
    "imaging-studies": (dto.ImagingStudy, db.ImagingStudy, "performed_at"),
    "referrals": (dto.Referral, db.Referral, "ordered_at"),
}


class ClinicalRecordService:
    def __init__(self, repository: HospitalRepository):
        self.repository = repository

    async def patients(
        self, query: str | None, limit: int, offset: int
    ) -> tuple[list[dto.PatientResponse], int]:
        records = await self.repository.patients()
        if query:
            records = [
                p
                for p in records
                if query.casefold()
                in " ".join([p.external_id, p.synthetic_mrn, p.display_name]).casefold()
            ]
        return [await self.patient_dto(p) for p in records[offset : offset + limit]], len(records)

    async def patient(self, patient_id: str) -> db.Patient:
        patient = await self.repository.get(db.Patient, patient_id)
        if patient is None:
            raise HospitalError()
        return patient

    async def patient_dto(self, patient: db.Patient) -> dto.PatientResponse:
        dataset = await self.repository.dataset(patient)
        return dto.PatientResponse(
            **patient.payload, case_id=dataset.case_id, created_at=patient.created_at
        )

    async def project(self, resource: str, record: Any) -> BaseModel:
        data = dict(record.payload)
        if resource == "documents":
            data.pop("storage_path", None)
            version = await self.repository.document_version(record)
            data["text_content"] = version.text_content if version else None
            data["has_asset"] = bool(version and version.artifact_id)
            # Metadata is not an evaluator channel: expose only documented display fields.
            data["metadata"] = {
                k: v
                for k, v in data.get("metadata", {}).items()
                if k in {"department", "width", "height", "synthetic_label"}
            }
        return RESOURCES[resource][0].model_validate(data)

    async def get(self, resource: str, external_id: str) -> BaseModel:
        record = await self.repository.get(RESOURCES[resource][1], external_id)
        if record is None:
            raise HospitalError()
        return await self.project(resource, record)

    async def list_records(
        self, resource: str, patient_id: str, filters: dict[str, Any]
    ) -> tuple[list[BaseModel], int]:
        patient = await self.patient(patient_id)
        records = await self.repository.for_patient(RESOURCES[resource][1], patient)
        data = [await self.project(resource, record) for record in records]
        date_field = RESOURCES[resource][2]
        # Internal tool capability: medication order chronology is distinct from start_at.
        if filters.get("_time_field") == "ordered_at" and resource == "medications":
            date_field = "ordered_at"
        start, end = filters.get("start_at"), filters.get("end_at")
        if start and end and start > end:
            raise HospitalError("VALIDATION_ERROR", 422)
        for key, value in filters.items():
            if value is None or key in {
                "limit",
                "offset",
                "start_at",
                "end_at",
                "sort",
                "event_types",
                "_time_field",
                "_sort",
                "_casefold",
                "q",
            }:
                continue
            data = [
                item
                for item in data
                if (
                    str(getattr(item, key, "")).casefold() == value.casefold()
                    if filters.get("_casefold")
                    and key in {"test_name", "medication_name", "body_region"}
                    and isinstance(value, str)
                    else getattr(item, key, None) == value
                )
            ]

        query = filters.get("q")
        if query:
            if resource != "documents":
                raise HospitalError("VALIDATION_ERROR", 422)
            data = [
                item
                for item in data
                if query.casefold()
                in f"{getattr(item, 'title', '')} {getattr(item, 'text_content', '')}".casefold()
            ]

        def in_range(item: BaseModel) -> bool:
            raw = getattr(item, date_field, None)
            time = as_instant(raw)
            return (not start or time is not None and time >= start) and (
                not end or time is not None and time <= end
            )

        data = [item for item in data if in_range(item)]
        # Stable secondary IDs ascending even when clinical time descends; unknown last.
        data.sort(key=lambda item: cast(Any, item).id)
        known = [item for item in data if as_instant(getattr(item, date_field, None)) is not None]
        unknown = [item for item in data if as_instant(getattr(item, date_field, None)) is None]
        known.sort(
            key=lambda item: (
                as_instant(getattr(item, date_field)) or datetime.min.replace(tzinfo=UTC)
            ),
            reverse=filters.get("_sort", "desc" if resource == "encounters" else "asc") == "desc",
        )
        data = known + unknown
        total = len(data)
        offset, limit = filters.get("offset", 0), filters.get("limit", 20)
        return data[offset : offset + limit], total

    async def encounter_records(self, encounter_id: str) -> dto.EncounterRecords:
        encounter = await self.repository.get(db.Encounter, encounter_id)
        if encounter is None:
            raise HospitalError()
        patient = await self.repository.by_id(db.Patient, encounter.patient_id)
        if patient is None:
            raise HospitalError()
        fields = {
            "clinical_event_ids": "clinical-events",
            "observation_ids": "observations",
            "medication_ids": "medications",
            "document_ids": "documents",
            "diagnosis_ids": "diagnoses",
        }
        refs = {}
        for key, resource in fields.items():
            records = await self.repository.for_patient(RESOURCES[resource][1], patient)
            refs[key] = sorted(
                record.external_id for record in records if record.encounter_id == encounter.id
            )
        return dto.EncounterRecords(encounter_id=encounter_id, **refs)

    async def lab_series(
        self, patient_id: str, test_code: str, filters: dict[str, Any]
    ) -> dto.LabSeries:
        patient = await self.patient(patient_id)
        records = await self.repository.for_patient(db.LabResult, patient)
        start, end = filters.get("start_at"), filters.get("end_at")
        if start and end and start > end:
            raise HospitalError("VALIDATION_ERROR", 422)
        points = [
            dto.LabPoint(
                observation_id=r.external_id,
                collected_at=r.collected_at,
                value_numeric=r.value_numeric,
                unit=r.unit,
            )
            for r in records
            if r.analyte_code == test_code
            and r.value_numeric is not None
            and (not start or r.collected_at is not None and r.collected_at >= start)
            and (not end or r.collected_at is not None and r.collected_at <= end)
        ]
        if len({point.unit for point in points}) > 1:
            raise HospitalError("RESOURCE_CONFLICT", 409)
        points.sort(key=lambda point: point.observation_id)
        points.sort(key=lambda point: point.collected_at or datetime.max.replace(tzinfo=UTC))
        return dto.LabSeries(patient_id=patient_id, test_code=test_code, points=points)

    async def search_documents(
        self, patient_id: str, query: str, filters: dict[str, Any]
    ) -> tuple[list[dto.DocumentSearchHit], int]:
        patient = await self.patient(patient_id)
        start, end = filters.get("start_at"), filters.get("end_at")
        if start and end and start > end:
            raise HospitalError("VALIDATION_ERROR", 422)
        hits = []
        for record in await self.repository.for_patient(db.ClinicalDocument, patient):
            document = dto.DocumentResponse.model_validate(
                (await self.project("documents", record)).model_dump()
            )
            text = document.text_content or ""
            position = text.casefold().find(query.casefold())
            if position < 0 and query.casefold() not in document.title.casefold():
                continue
            if filters.get("document_type") and document.document_type != filters["document_type"]:
                continue
            if filters.get("encounter_id") and document.encounter_id != filters["encounter_id"]:
                continue
            if (
                filters.get("department")
                and document.metadata.get("department") != filters["department"]
            ):
                continue
            if (start and (document.event_at is None or document.event_at < start)) or (
                end and (document.event_at is None or document.event_at > end)
            ):
                continue
            begin = max(0, position - 40)
            hits.append(
                dto.DocumentSearchHit(
                    id=document.id,
                    title=document.title,
                    document_type=document.document_type,
                    event_at=document.event_at,
                    snippet=text[begin : begin + 240],
                    relevance_score=1.0,
                )
            )
        # Exact case-insensitive substring matches are unranked (all score 1).
        hits.sort(key=lambda hit: hit.id)
        total = len(hits)
        offset, limit = filters.get("offset", 0), filters.get("limit", 20)
        return hits[offset : offset + limit], total

    async def imaging_report(self, study_id: str) -> BaseModel:
        study = await self.repository.get(db.ImagingStudy, study_id)
        if study is None or study.report_document_id is None:
            raise HospitalError()
        document = await self.repository.by_id(db.ClinicalDocument, study.report_document_id)
        if document is None or document.patient_id != study.patient_id:
            raise HospitalError()
        return await self.project("documents", document)

    async def summary(self, patient_id: str) -> dto.PatientSummary:
        patient = await self.patient(patient_id)
        counts = {}
        for resource in [
            "encounters",
            "documents",
            "observations",
            "medications",
            "imaging-studies",
        ]:
            counts[resource] = await self.repository.for_patient(RESOURCES[resource][1], patient)
        encounters = counts["encounters"]
        return dto.PatientSummary(
            patient_id=patient_id,
            encounter_count=len(encounters),
            document_count=len(counts["documents"]),
            observation_count=len(counts["observations"]),
            medication_count=len(counts["medications"]),
            imaging_study_count=len(counts["imaging-studies"]),
            latest_encounter_at=max((r.started_at for r in encounters), default=None),
        )

    async def timeline(
        self, patient_id: str, filters: dict[str, Any]
    ) -> tuple[list[dto.TimelineEntry], int]:
        if filters.get("q"):
            raise HospitalError("VALIDATION_ERROR", 422)
        patient = await self.patient(patient_id)
        entries = []
        types = {
            "encounters": "encounter",
            "clinical-events": "clinical_event",
            "observations": "observation",
            "medications": "medication",
            "documents": "document",
            "imaging-studies": "imaging_study",
            "referrals": "referral",
        }
        types.update(
            {
                "diagnoses": "diagnosis",
                "symptoms": "symptom",
                "diagnostic-reports": "diagnostic_report",
            }
        )
        for resource, (_, model, time_field) in RESOURCES.items():
            for record in await self.repository.for_patient(model, patient):
                item = await self.project(resource, record)
                data = item.model_dump()
                timestamp = as_instant(data.get(time_field))
                if timestamp is None:
                    continue
                title = next(
                    (
                        str(data[k])
                        for k in [
                            "title",
                            "test_name",
                            "medication_name",
                            "department",
                            "body_region",
                            "description",
                            "reason",
                        ]
                        if data.get(k)
                    ),
                    record.external_id,
                )
                entries.append(
                    dto.TimelineEntry(
                        id=f"TL-{resource}-{record.external_id}",
                        patient_id=patient_id,
                        event_type=types[resource],
                        timestamp=timestamp,
                        timestamp_type=time_field,
                        title=title,
                        description=f"Source {types[resource]} record",
                        source_ref=dto.SourceRef(type=types[resource], id=record.external_id),
                        encounter_id=data.get("encounter_id")
                        if resource != "encounters"
                        else record.external_id,
                        timestamps={
                            key: value.isoformat() if isinstance(value, datetime) else value
                            for key, value in data.items()
                            if key.endswith("_at")
                        },
                    )
                )
        start, end = filters.get("start_at"), filters.get("end_at")
        if start and end and start > end:
            raise HospitalError("VALIDATION_ERROR", 422)
        event_types = filters.get("event_types")
        entries = [
            e
            for e in entries
            if (not start or e.timestamp >= start)
            and (not end or e.timestamp <= end)
            and (not event_types or e.event_type in event_types.split(","))
            and (not filters.get("encounter_id") or e.encounter_id == filters["encounter_id"])
        ]
        entries.sort(key=lambda e: e.id)
        entries.sort(key=lambda e: e.timestamp, reverse=filters.get("sort") == "desc")
        total = len(entries)
        offset, limit = filters.get("offset", 0), filters.get("limit", 20)
        return entries[offset : offset + limit], total


def as_instant(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, str) and len(value) > 10:
        return datetime.fromisoformat(value).astimezone(UTC)
    return None
