"""Deterministic maintenance importer: validate first, commit clinical rows once."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.hospital.schemas import Document, ImagingAsset
from app.hospital.validation import ValidatedCase
from app.models import hospital as db


class ImportConflict(ValueError):
    pass


def stable_id(case_id: str, version: str, kind: str, external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, json.dumps(["casetrace", case_id, version, kind, external_id]))


def instant(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value and len(value) > 10 else None


def import_fingerprint(validated: ValidatedCase) -> str:
    """Frozen clinical/asset identity shared by preflight discovery and persistence."""
    case = validated.clinical
    payload = case.model_dump(mode="json")
    content = {
        "clinical": payload,
        "assets": {key: info.sha256 for key, info in sorted(validated.assets.items())},
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def ingest(session: AsyncSession, validated: ValidatedCase) -> dict[str, object]:
    case = validated.clinical
    payload = case.model_dump(mode="json")
    seed_hash = import_fingerprint(validated)

    def uid(kind: str, value: str) -> UUID:
        return stable_id(case.case_id, case.version, kind, value)

    def ref(kind: str, value: str | None) -> UUID | None:
        return uid(kind, value) if value else None

    def source(record: Any) -> dict[str, object]:
        return {
            "id": uid(record.__class__.__name__, record.id),
            "external_id": record.id,
            "source_version": 1,
            "source_system": "synthetic_his",
            "created_at": case.created_at,
            "updated_at": case.updated_at,
            "payload": record.model_dump(mode="json"),
        }

    def scoped(record: Any) -> dict[str, object]:
        return {
            **source(record),
            "patient_id": uid("Patient", case.patient.id),
            "encounter_id": ref("Encounter", record.encounter_id),
        }

    def linked(record: Any) -> dict[str, object]:
        return {**scoped(record), "source_document_id": ref("Document", record.source_document_id)}

    counts = {key: len(value) for key, value in payload.items() if isinstance(value, list)}
    summary: dict[str, object] = {
        "case_id": case.case_id,
        "version": case.version,
        "counts": counts,
        "import_id": str(uid("dataset", case.case_id)),
        "source_hash": seed_hash,
    }
    try:
        async with session.begin():
            existing = await session.scalar(
                select(db.CaseDataset).where(
                    db.CaseDataset.case_id == case.case_id,
                    db.CaseDataset.dataset_version == case.version,
                )
            )
            if existing:
                if existing.seed_hash != seed_hash:
                    raise ImportConflict(
                        "case/version already exists with different clinical content or asset bytes"
                    )
                return {**summary, "status": "unchanged"}
            dataset_id = uid("dataset", case.case_id)
            session.add(
                db.CaseDataset(
                    id=dataset_id,
                    case_id=case.case_id,
                    dataset_version=case.version,
                    seed_hash=seed_hash,
                    status="ready",
                    seeded_at=datetime.now(UTC),
                )
            )
            await session.flush()
            p = case.patient
            session.add(
                db.Patient(
                    **source(p),
                    dataset_id=dataset_id,
                    synthetic_mrn=p.synthetic_identifier,
                    display_name=p.display_name,
                    birth_date=p.date_of_birth,
                    sex=p.sex,
                    is_synthetic=True,
                )
            )
            await session.flush()
            for record_1 in case.encounters:
                session.add(
                    db.Encounter(
                        **source(record_1),
                        patient_id=uid("Patient", p.id),
                        type=record_1.encounter_type,
                        status=record_1.status,
                        department=record_1.department,
                        provider_name=record_1.provider_name,
                        started_at=record_1.started_at,
                        ended_at=record_1.ended_at,
                    )
                )
            await session.flush()
            asset_records: list[Document | ImagingAsset] = [*case.documents, *case.imaging_assets]
            for record_2 in asset_records:
                if record_2.id in validated.assets:
                    info = validated.assets[record_2.id]
                    session.add(
                        db.Asset(
                            id=uid("asset", record_2.id),
                            external_id=f"{record_2.id}-asset",
                            storage_key=info.key,
                            mime_type=record_2.mime_type,
                            sha256=info.sha256,
                            byte_size=info.byte_size,
                            synthetic_label="SYNTHETIC — NOT FOR CLINICAL USE",
                            created_at=case.created_at,
                        )
                    )
            await session.flush()
            for record_3 in case.documents:
                session.add(
                    db.ClinicalDocument(
                        **scoped(record_3),
                        document_type=record_3.document_type,
                        title=record_3.title,
                        mime_type=record_3.mime_type,
                        author_label=record_3.author,
                        event_at=record_3.event_at,
                        authored_at=record_3.authored_at,
                        current_version_id=None,
                    )
                )
            await session.flush()
            for record_4 in case.documents:
                version_id = uid("document_version", record_4.id)
                session.add(
                    db.DocumentVersion(
                        id=version_id,
                        document_id=uid("Document", record_4.id),
                        version_number=1,
                        artifact_id=uid("asset", record_4.id)
                        if record_4.id in validated.assets
                        else None,
                        text_content=record_4.text_content,
                        content_hash=hashlib.sha256(
                            (record_4.text_content or "").encode()
                        ).hexdigest(),
                    )
                )
            await session.flush()
            for record_5 in case.documents:
                document = await session.get(db.ClinicalDocument, uid("Document", record_5.id))
                assert document is not None
                document.current_version_id = uid("document_version", record_5.id)
            for record_6 in case.clinical_events:
                session.add(
                    db.ClinicalEvent(
                        **linked(record_6),
                        event_type=record_6.event_type,
                        event_time=record_6.occurred_at,
                        time_precision="instant" if record_6.occurred_at else "unknown",
                        time_raw=record_6.occurred_at.isoformat() if record_6.occurred_at else None,
                        documented_at=record_6.documented_at,
                        description=record_6.description,
                    )
                )
            for record_7 in case.observations:
                session.add(
                    db.LabResult(
                        **linked(record_7),
                        analyte_code=record_7.test_code,
                        test_name=record_7.test_name,
                        value_numeric=record_7.value_numeric,
                        value_text=record_7.value_text,
                        unit=record_7.unit,
                        reference_low=record_7.reference_range_low,
                        reference_high=record_7.reference_range_high,
                        collected_at=record_7.specimen_collected_at,
                        reported_at=record_7.reported_at,
                        status=record_7.status,
                    )
                )
            for record_8 in case.medications:
                session.add(
                    db.MedicationEvent(
                        **linked(record_8),
                        drug_name=record_8.medication_name,
                        generic_name=record_8.generic_name,
                        dose=record_8.dose,
                        unit=record_8.dose_unit,
                        route=record_8.route,
                        frequency=record_8.frequency,
                        ordered_at=record_8.ordered_at,
                        effective_at=instant(record_8.start_at),
                        discontinued_at=instant(record_8.end_at),
                        prescriber=record_8.prescriber,
                        status=record_8.status,
                    )
                )
            for record_9 in case.imaging_studies:
                session.add(
                    db.ImagingStudy(
                        **scoped(record_9),
                        modality=record_9.modality,
                        body_region=record_9.body_region,
                        performed_at=record_9.performed_at,
                        reported_at=record_9.reported_at,
                        status=record_9.status,
                        report_document_id=ref("Document", record_9.report_document_id),
                    )
                )
            for record_10 in case.referrals:
                session.add(
                    db.Referral(
                        **scoped(record_10),
                        origin_service=record_10.referring_department,
                        destination_service=record_10.referred_department,
                        reason=record_10.reason,
                        requested_at=record_10.ordered_at,
                        scheduled_at=record_10.appointment_at,
                        status=record_10.status,
                    )
                )
            await session.flush()
            for record_11 in case.imaging_assets:
                session.add(
                    db.ImagingAsset(
                        id=uid("ImagingAsset", record_11.id),
                        external_id=record_11.id,
                        study_id=uid("ImagingStudy", record_11.imaging_study_id),
                        asset_id=uid("asset", record_11.id),
                        asset_kind=record_11.asset_type,
                        payload=record_11.model_dump(mode="json"),
                    )
                )
            for diagnosis in case.diagnoses:
                session.add(
                    db.Diagnosis(
                        **scoped(diagnosis),
                        name=diagnosis.name,
                        code_system=diagnosis.code_system,
                        code=diagnosis.code,
                        status=diagnosis.status,
                        diagnosed_at=instant(diagnosis.diagnosed_at),
                    )
                )
            for symptom in case.symptoms:
                session.add(
                    db.Symptom(
                        **scoped(symptom),
                        name=symptom.name,
                        onset_at=instant(symptom.onset_at),
                        severity=symptom.severity,
                        frequency=symptom.frequency,
                        status=symptom.status,
                        description=symptom.description,
                    )
                )
            for report in case.diagnostic_reports:
                session.add(
                    db.DiagnosticReport(
                        **scoped(report),
                        report_type=report.report_type,
                        title=report.title,
                        status=report.status,
                        issued_at=report.issued_at,
                        conclusion=report.conclusion,
                        document_id=ref("Document", report.document_id),
                        imaging_study_id=ref("ImagingStudy", report.imaging_study_id),
                    )
                )
            await session.flush()
            for report in case.diagnostic_reports:
                for observation_id in report.observation_ids:
                    session.add(
                        db.ReportObservation(
                            report_id=uid("DiagnosticReport", report.id),
                            observation_id=uid("Observation", observation_id),
                        )
                    )
            await session.flush()
    except IntegrityError as exc:
        raise ImportConflict(
            "import rolled back: duplicate source ID or invalid clinical relationship"
        ) from exc
    return {**summary, "status": "imported"}
