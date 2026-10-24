"""Executable tool arguments; historical record_id selectors remain supported."""

from typing import Annotated, Literal, Self

from pydantic import AliasChoices, AwareDatetime, Field, model_validator

from app.hospital.schemas import ClinicalModel, Identifier

Text = Annotated[str, Field(min_length=1, max_length=200)]


class PatientInput(ClinicalModel):
    patient_id: Identifier


class PatientSearchInput(PatientInput):
    query: str = Field(default="", max_length=200)


class PageInput(PatientInput):
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)

    @model_validator(mode="after")
    def ordered_range(self) -> Self:
        if self.start_at and self.end_at and self.start_at > self.end_at:
            raise ValueError("start_at must not follow end_at")
        return self


class EncounterInput(PageInput):
    department: Text | None = None
    encounter_type: (
        Literal[
            "outpatient",
            "inpatient",
            "emergency",
            "specialist",
            "telemedicine",
            "laboratory",
            "radiology",
            "procedure",
            "follow_up",
        ]
        | None
    ) = None
    status: Text | None = None


class ScopedPageInput(PageInput):
    encounter_id: Identifier | None = None


class DocumentSearchInput(ScopedPageInput):
    query: str = Field(default="", max_length=200)
    document_type: Text | None = None
    department: Text | None = None


class LabInput(ScopedPageInput):
    test_name: Text | None = None
    test_code: Text | None = None
    status: Literal["ordered", "preliminary", "final", "corrected", "cancelled"] | None = None


class MedicationInput(ScopedPageInput):
    medication_name: Text | None = None
    status: Literal["ordered", "active", "discontinued", "held", "completed", "unknown"] | None = (
        None
    )


class ReportInput(ScopedPageInput):
    report_type: Literal["laboratory", "radiology", "pathology", "cardiology", "other"] | None = (
        None
    )
    imaging_study_id: Identifier | None = None


class ImagingInput(ScopedPageInput):
    modality: (
        Literal["X_RAY", "CT", "MRI", "ULTRASOUND", "ECG", "ECHOCARDIOGRAM", "OTHER"] | None
    ) = None
    body_region: Text | None = None
    imaging_study_id: Identifier | None = None


class ReferralInput(ScopedPageInput):
    status: (
        Literal["ordered", "scheduled", "completed", "cancelled", "no_show", "unknown"] | None
    ) = None
    department: Text | None = None


class ExactInput(PatientInput):
    record_id: Identifier
    encounter_id: Identifier | None = None
    source_version: int | None = Field(default=None, ge=1)
    source_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class EncounterDetailInput(PatientInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "encounter_id"))
    source_version: int | None = Field(default=None, ge=1)
    source_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class DocumentInput(ExactInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "document_id"))


class ObservationInput(ExactInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "observation_id"))


class MedicationDetailInput(ExactInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "medication_id"))


class ReportDetailInput(ExactInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "report_id"))


class AssetInput(ExactInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "imaging_asset_id"))


class ImagingReportInput(ExactInput):
    record_id: Identifier = Field(validation_alias=AliasChoices("record_id", "imaging_study_id"))


class ComparisonInput(PatientInput):
    record_id: Identifier | None = None
    other_id: Identifier | None = None
    test_name: Text | None = None
    test_code: Text | None = None

    @model_validator(mode="after")
    def selection(self) -> Self:
        pair = self.record_id is not None or self.other_id is not None
        analyte = self.test_name is not None or self.test_code is not None
        if pair == analyte or pair and (not self.record_id or not self.other_id):
            raise ValueError("provide a complete record_id/other_id pair OR an analyte selector")
        if pair and self.record_id == self.other_id:
            raise ValueError("comparison requires distinct observations")
        return self


TimelineCategory = Literal[
    "encounters",
    "events",
    "observations",
    "medications",
    "documents",
    "imaging_studies",
    "diagnostic_reports",
    "referrals",
    "diagnoses",
    "symptoms",
]


class TimelineInput(ScopedPageInput):
    include: list[TimelineCategory] = Field(default=["events"], min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_categories(self) -> Self:
        if len(set(self.include)) != len(self.include):
            raise ValueError("include must contain unique categories")
        return self


INPUT_MODELS: dict[str, type[PatientInput]] = {
    "get_patient": PatientInput,
    "search_patient": PatientSearchInput,
    "get_encounters": EncounterInput,
    "get_encounter": EncounterDetailInput,
    "search_clinical_notes": DocumentSearchInput,
    "get_clinical_note": DocumentInput,
    "search_documents": DocumentSearchInput,
    "get_document": DocumentInput,
    "get_lab_results": LabInput,
    "get_lab_result": ObservationInput,
    "compare_lab_results": ComparisonInput,
    "get_medication_history": MedicationInput,
    "get_medication": MedicationDetailInput,
    "get_diagnostic_reports": ReportInput,
    "get_diagnostic_report": ReportDetailInput,
    "get_imaging_studies": ImagingInput,
    "get_imaging_asset_metadata": AssetInput,
    "get_imaging_report": ImagingReportInput,
    "get_referrals": ReferralInput,
    "build_patient_timeline": TimelineInput,
}
