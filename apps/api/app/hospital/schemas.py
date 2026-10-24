"""Canonical clinical input and hospital DTOs. Evaluation data has no runtime model."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[
    str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
]


class ClinicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("*", mode="after")
    @classmethod
    def aware_times(cls, value: object) -> object:
        if isinstance(value, datetime) and value.utcoffset() is None:
            raise ValueError("clinical instants require an explicit UTC offset")
        return value


class Patient(ClinicalModel):
    id: Identifier
    synthetic_identifier: str
    display_name: str
    date_of_birth: date
    sex: Literal["male", "female", "other", "unknown"]


class PatientResponse(Patient):
    case_id: str
    created_at: datetime


class Scoped(ClinicalModel):
    id: Identifier
    patient_id: Identifier
    encounter_id: Identifier | None = None


class Encounter(ClinicalModel):
    id: Identifier
    patient_id: Identifier
    encounter_type: Literal[
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
    department: str
    provider_name: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str

    @model_validator(mode="after")
    def chronology(self) -> "Encounter":
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError(f"{self.id}: ended_at precedes started_at")
        return self


class ClinicalEvent(Scoped):
    event_type: str
    occurred_at: datetime | None = None
    documented_at: datetime | None = None
    description: str
    source_document_id: Identifier | None = None


class Observation(Scoped):
    test_code: str | None = None
    test_name: str
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    status: Literal["ordered", "preliminary", "final", "corrected", "cancelled"]
    specimen_collected_at: datetime | None = None
    reported_at: datetime | None = None
    source_document_id: Identifier | None = None

    @model_validator(mode="after")
    def result_integrity(self) -> "Observation":
        if (
            self.status in {"final", "corrected", "preliminary"}
            and self.value_numeric is None
            and self.value_text is None
        ):
            raise ValueError(f"{self.id}: completed result needs a value")
        if (
            self.specimen_collected_at
            and self.reported_at
            and self.reported_at < self.specimen_collected_at
        ):
            raise ValueError(f"{self.id}: reported_at precedes specimen collection")
        if (
            self.reference_range_low is not None
            and self.reference_range_high is not None
            and self.reference_range_low > self.reference_range_high
        ):
            raise ValueError(f"{self.id}: inverted reference range")
        return self


class Medication(Scoped):
    medication_name: str
    generic_name: str | None = None
    dose: float | None = None
    dose_unit: str | None = None
    route: str | None = None
    frequency: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    status: Literal["ordered", "active", "discontinued", "held", "completed", "unknown"]
    prescriber: str | None = None
    ordered_at: datetime | None = None
    source_document_id: Identifier | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def date_or_instant(cls, value: str | None) -> str | None:
        if value is not None:
            if len(value) == 10:
                date.fromisoformat(value)
            else:
                parsed = datetime.fromisoformat(value)
                if parsed.utcoffset() is None:
                    raise ValueError("medication instants require offset; date-only stays a date")
        return value

    @model_validator(mode="after")
    def chronology(self) -> "Medication":
        if self.start_at and self.end_at:
            # Only compare matching precision. Mixed precision is indeterminate.
            if len(self.start_at) == 10 and len(self.end_at) == 10:
                if date.fromisoformat(self.end_at) < date.fromisoformat(self.start_at):
                    raise ValueError(f"{self.id}: end_at precedes start_at")
            elif len(self.start_at) > 10 and len(self.end_at) > 10:
                if datetime.fromisoformat(self.end_at) < datetime.fromisoformat(self.start_at):
                    raise ValueError(f"{self.id}: end_at precedes start_at")
        return self


class Document(Scoped):
    document_type: str
    title: str
    author: str | None = None
    event_at: datetime | None = None
    authored_at: datetime | None = None
    mime_type: Literal["application/pdf", "image/png", "image/jpeg", "text/plain", "text/html"] = (
        "text/plain"
    )
    text_content: str | None = None
    storage_path: str | None = None
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def clinical_metadata(
        cls, value: dict[str, str | int | bool | None]
    ) -> dict[str, str | int | bool | None]:
        if set(value) - {"department", "width", "height", "synthetic_label"}:
            raise ValueError(
                "unsupported clinical metadata key; evaluator annotations are forbidden"
            )
        return value


class DocumentResponse(Scoped):
    document_type: str
    title: str
    author: str | None
    event_at: datetime | None
    authored_at: datetime | None
    mime_type: str
    text_content: str | None
    has_asset: bool
    metadata: dict[str, str | int | bool | None]


class ImagingStudy(Scoped):
    modality: Literal["X_RAY", "CT", "MRI", "ULTRASOUND", "ECG", "ECHOCARDIOGRAM", "OTHER"]
    body_region: str
    performed_at: datetime | None = None
    reported_at: datetime | None = None
    status: str
    report_document_id: Identifier | None = None


class ImagingAsset(ClinicalModel):
    id: Identifier
    imaging_study_id: Identifier
    asset_type: str
    mime_type: Literal["image/png", "image/jpeg"]
    storage_path: str
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def clinical_metadata(
        cls, value: dict[str, str | int | bool | None]
    ) -> dict[str, str | int | bool | None]:
        if set(value) - {"department", "width", "height", "synthetic_label"}:
            raise ValueError(
                "unsupported clinical metadata key; evaluator annotations are forbidden"
            )
        return value


class ImagingAssetResponse(ClinicalModel):
    id: str
    imaging_study_id: str
    asset_type: str
    mime_type: str
    width: int | None
    height: int | None
    metadata: dict[str, str | int | bool | None]


class Referral(Scoped):
    referring_department: str
    referred_department: str
    reason: str
    ordered_at: datetime | None = None
    appointment_at: datetime | None = None
    status: Literal["ordered", "scheduled", "completed", "cancelled", "no_show", "unknown"]


class Diagnosis(Scoped):
    name: str
    code_system: str | None = None
    code: str | None = None
    status: Literal["suspected", "provisional", "confirmed", "resolved", "historical", "ruled_out"]
    diagnosed_at: str | None = None

    @field_validator("diagnosed_at")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        return Medication.date_or_instant(value)


class Symptom(Scoped):
    name: str
    onset_at: str | None = None
    severity: str | None = None
    frequency: str | None = None
    status: str
    description: str | None = None

    @field_validator("onset_at")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        return Medication.date_or_instant(value)


class DiagnosticReport(Scoped):
    report_type: Literal["laboratory", "radiology", "pathology", "cardiology", "other"]
    title: str
    status: str
    issued_at: datetime | None = None
    conclusion: str | None = None
    document_id: Identifier | None = None
    observation_ids: list[Identifier] = Field(default_factory=list)
    imaging_study_id: Identifier | None = None


class ClinicalCase(ClinicalModel):
    case_id: Identifier
    version: str = Field(min_length=1)
    status: Literal["draft", "validating", "ready", "deprecated"]
    created_at: datetime
    updated_at: datetime
    patient: Patient
    encounters: list[Encounter] = Field(default_factory=list)
    clinical_events: list[ClinicalEvent] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    imaging_studies: list[ImagingStudy] = Field(default_factory=list)
    imaging_assets: list[ImagingAsset] = Field(default_factory=list)
    referrals: list[Referral] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    symptoms: list[Symptom] = Field(default_factory=list)
    diagnostic_reports: list[DiagnosticReport] = Field(default_factory=list)


class Meta(BaseModel):
    request_id: str


class Pagination(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool


class ResourceResponse[T](BaseModel):
    data: T
    meta: Meta


class CollectionResponse[T](ResourceResponse[list[T]]):
    pagination: Pagination


class SourceRef(BaseModel):
    type: str
    id: str


class TimelineEntry(BaseModel):
    id: str
    patient_id: str
    event_type: str
    timestamp: datetime
    timestamp_type: str
    title: str
    description: str
    source_ref: SourceRef
    encounter_id: str | None = None
    timestamps: dict[str, str | None] = Field(default_factory=dict)
    time_precision: Literal["instant"] = "instant"


class PatientSummary(BaseModel):
    patient_id: str
    encounter_count: int
    document_count: int
    observation_count: int
    medication_count: int
    imaging_study_count: int
    latest_encounter_at: datetime | None


class EncounterRecords(BaseModel):
    encounter_id: str
    clinical_event_ids: list[str]
    observation_ids: list[str]
    medication_ids: list[str]
    document_ids: list[str]
    diagnosis_ids: list[str]


class LabPoint(BaseModel):
    observation_id: str
    collected_at: datetime | None
    value_numeric: float
    unit: str | None


class LabSeries(BaseModel):
    patient_id: str
    test_code: str
    points: list[LabPoint]


class DocumentSearchHit(BaseModel):
    id: str
    title: str
    document_type: str
    event_at: datetime | None
    snippet: str
    relevance_score: float


class HospitalErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class HospitalErrorResponse(BaseModel):
    error: HospitalErrorDetail
    meta: Meta
