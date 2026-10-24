# CASETRACE — Hospital API Contract

## Refactor 08 additive discovery contract

`GET /api/hospital/v1/cases` returns the existing collection envelope with
`case_id`, nullable `version`, `patient_id`, `display_name`, `latest_encounter_at`,
`status`, `imported` (persisted patient exists), nullable `dataset_status`, `counts` (canonical category names), and `modalities` (registered document
MIME types and imaging modalities). Stable case-ID ordering; limit 1–100, offset,
exact case_id/status/modality filters. `GET /cases/{case_id}` returns the resource
envelope; locally absent requested cases return status `not_present`, production
unknown cases return 404. Only actual canonical directories are listed.

Imported identities/counts/modalities come from hospital repositories. In local
development/test, maintenance discovery additionally reports `available_not_imported`,
`invalid`, `missing_assets`, `source_conflict`, or `not_present`. Production never
reads canonical inputs. Missing maintenance files do not make persisted records
unavailable. A conflict/invalid source disables launching from the catalog while
the existing imported patient chart remains accessible. Read sessions close before
off-thread validation/hashing. No validator diagnostics, filenames, manifest fields,
editor annotations, summaries, answer labels or evaluator fields are published.
No migration, clinical DTO change, tool permission change or ingestion occurs.

MVP persistence is SQLite via SQLAlchemy 2.x asyncio and aiosqlite. Clinical tools retain their service/repository boundary. Follow [development stack](development-stack.md) for short read sessions, connection settings, portable types and maintenance-only seeding; no database session is passed to agents.

**File:** `docs/hospital-api.md`  
**Status:** Canonical — v1  
**System:** CASETRACE Simulated Hospital Information System  
**Backend:** FastAPI · SQLite · SQLAlchemy 2 · Pydantic v2
**Related documents:** `AGENTS.md`, `case-schema.md`, `agent-tools.md`, `backend-architecture.md`, `frontend-backend-contract.md`

---

## 1. Purpose

This document defines the REST API contract for the CASETRACE Simulated Hospital Information System.

The simulated hospital is a realistic, read-only clinical record environment containing synthetic longitudinal patient histories.

It serves two consumers:

1. **Hospital frontend:** Displays patient records, encounters, laboratory results, medications, clinical documents, imaging studies, and referrals.
2. **CASETRACE agent tool layer:** Retrieves clinical evidence through a controlled `ClinicalRecordService` abstraction.

The hospital API must behave like an independent clinical information system, even when deployed within the same FastAPI application as CASETRACE.

### Primary objectives

- Expose realistic longitudinal patient records.
- Preserve clinical timestamps and source provenance.
- Support structured and unstructured clinical information.
- Support multimodal assets, including PDFs and images.
- Enforce patient-level access controls.
- Provide predictable filtering, sorting, and pagination.
- Allow the hospital frontend to browse records independently of investigations.
- Allow the tool layer to retrieve identical clinical records without direct agent database access.
- Remain compatible with a future FHIR-based hospital adapter.

The API must not expose the intended mystery, expected answers, ground truth, or evaluation metadata.

---

## 2. System Boundaries

CASETRACE consists of two logical systems.

### A. Simulated Hospital

Responsible for clinical records.

```text
Hospital UI
    |
    v
Hospital REST API
    |
    v
ClinicalRecordService
    |
    v
SimulatedHospitalService
    |
    v
Clinical Repositories
    |
    v
SQLite + Asset Storage
```

### B. CASETRACE Investigation Engine

Responsible for investigating those records.

```text
Investigation UI
    |
    v
Investigation API
    |
    v
Orchestration Engine
    |
    v
Specialized Agents
    |
    v
Tool Registry
    |
    v
ClinicalRecordService
    |
    v
Simulated Hospital Data
```

### Architectural rule

The hospital frontend communicates with the hospital REST API.

Agents communicate with registered tools.

Tools communicate with the `ClinicalRecordService`.

**Agents must never directly call hospital REST endpoints, access SQLAlchemy sessions, or query SQLite.**

In the initial monolith, the tool layer may call the clinical service in-process. An HTTP adapter can be introduced later without changing agent behavior.

---

## 3. API Namespace

All hospital endpoints use:

```http
/api/hospital/v1
```

Examples:

```http
GET /api/hospital/v1/patients
GET /api/hospital/v1/patients/PAT-001
GET /api/hospital/v1/patients/PAT-001/encounters
GET /api/hospital/v1/patients/PAT-001/observations
GET /api/hospital/v1/documents/DOC-001
```

Investigation endpoints remain separate:

```http
/api/investigations
```

This namespace is the canonical v1 hospital contract. Any legacy routes such as `/api/patients` should be removed or implemented as explicit compatibility aliases, not maintained as a second independent API.

---

## 4. API Design Principles

### 4.1 RESTful resource structure

Use plural resource names:

```text
patients
encounters
clinical-events
observations
medications
diagnoses
documents
diagnostic-reports
imaging-studies
imaging-assets
referrals
```

### 4.2 Stable identifiers

Clinical resource IDs must remain stable across API responses, tool results, database records, and evidence citations.

Example:

```text
PAT-001
ENC-001
EVT-001
LAB-001
MED-001
DOC-001
IMG-001
```

### 4.3 Read-only v1

The hospital API is read-only for the hackathon.

Supported methods:

```http
GET
HEAD
OPTIONS
```

Clinical record modification endpoints are out of scope.

Synthetic records are created or updated through controlled case-seeding workflows.

### 4.4 No clinical interpretation

Hospital endpoints return clinical records, not AI conclusions.

For example:

```json
{
  "test_name": "Hemoglobin",
  "value_numeric": 8.9,
  "unit": "g/dL"
}
```

The hospital API must not automatically claim that the value establishes a particular diagnosis or causal relationship.

### 4.5 Preserve provenance

All records must expose their stable IDs, relevant timestamps, and available source-document relationships.

---

## 5. Authentication and Authorization

The hospital API must use a centralized authorization dependency.

For the hackathon, a lightweight authenticated demo session is acceptable.

The API must not be publicly readable merely because its records are synthetic.

### Roles

| Role | Hospital records | Investigation data | Ground truth |
|---|---|---|---|
| `hospital_viewer` | Read authorized records | No access by default | Never |
| `investigator` | Read authorized records | Read/start investigations | Never |
| `admin` | Read and manage demo environment | Administrative access | No runtime access |
| `evaluator` | Separate offline evaluation workflow | Evaluation results | Evaluation environment only |

Ground truth is not exposed through any HTTP route, including administrative routes.

### Access scope

For v1, authenticated demo users may be granted access to a configured set of synthetic patients.

Authorization must still be enforced on individual resource lookups.

A document or imaging asset must not become accessible merely because its ID is known.

---

## 6. Standard Response Envelope

Successful single-resource responses use:

```json
{
  "data": {},
  "meta": {
    "request_id": "req-001"
  }
}
```

Successful collection responses use:

```json
{
  "data": [],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 0,
    "has_more": false
  },
  "meta": {
    "request_id": "req-001"
  }
}
```

### Rules

- `data` contains clinical resources.
- `pagination` appears on collection endpoints.
- `meta.request_id` supports tracing and debugging.
- Empty collections return `200 OK` with `data: []`.
- Missing single resources return `404 Not Found`.
- Responses must not contain ORM-specific internal objects.
- JSON property names use `snake_case`.

The hospital API envelope is distinct from the agent `ToolResult` contract.

The tool adapter is responsible for transforming clinical service results into:

```text
status
records
source_refs
metadata
retrieved_at
```

---

## 7. Standard Error Contract

All API errors use:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested clinical record was not found.",
    "details": {}
  },
  "meta": {
    "request_id": "req-001"
  }
}
```

### Error codes

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `INVALID_QUERY` | Invalid filter combination |
| 401 | `UNAUTHENTICATED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Access not permitted |
| 404 | `RESOURCE_NOT_FOUND` | Resource does not exist or is not accessible |
| 409 | `RESOURCE_CONFLICT` | Inconsistent resource state |
| 422 | `VALIDATION_ERROR` | Invalid request parameters |
| 429 | `RATE_LIMITED` | Request limit exceeded |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | Clinical service unavailable |

Do not expose SQL statements, stack traces, filesystem paths, or internal secrets in public error responses.

---

## 8. Date and Time Contract

Time semantics are essential to CASETRACE.

### API serialization

All timestamp fields must be RFC 3339 / ISO 8601 strings with explicit timezone offsets.

Example:

```json
{
  "occurred_at": "2026-01-18T14:30:00+03:00",
  "documented_at": "2026-01-20T09:15:00+03:00"
}
```

### Rules

- Store normalized instants in UTC where appropriate.
- Preserve original timezone or offset metadata when available.
- Never silently convert an event date into a documentation date.
- Never assume a date-only value means midnight.
- Unknown timestamps must be represented as `null`.
- Do not invent timestamps to fill missing clinical information.
- Sort chronologically by the explicitly requested timestamp type.

### Important distinctions

| Field | Meaning |
|---|---|
| `occurred_at` | When a clinical event happened |
| `documented_at` | When it was entered into the record |
| `event_at` | Time associated with a document's clinical content |
| `authored_at` | When the document was written |
| `ordered_at` | When a test, medication, or referral was ordered |
| `specimen_collected_at` | When a specimen was collected |
| `reported_at` | When a result or report became available |
| `performed_at` | When a procedure or imaging study occurred |

These fields must remain distinct across the database, API, tool layer, and frontend.

---

# PART I — PATIENT RESOURCES

## 9. Patient Resource

### Schema

```typescript
interface Patient {
  id: string;
  case_id: string;
  synthetic_identifier: string;
  display_name: string;
  date_of_birth: string;
  sex: "male" | "female" | "other" | "unknown";
  created_at: string;
}
```

`case_id` is a non-sensitive synthetic fixture identifier, not an investigation answer. It may be exposed to authorized demo clients, but agents should ordinarily receive only the patient identifier and clinically relevant fields.

### 9.1 List Patients

```http
GET /api/hospital/v1/patients
```

Query parameters:

| Parameter | Type | Description |
|---|---|---|
| `query` | string | Name, patient ID, or synthetic MRN |
| `limit` | integer | Default 20, maximum 100 |
| `offset` | integer | Default 0 |

Example:

```http
GET /api/hospital/v1/patients?query=Samuel&limit=20
```

Response:

```json
{
  "data": [
    {
      "id": "PAT-001",
      "case_id": "CASE-001",
      "synthetic_identifier": "MRN-SYN-000001",
      "display_name": "Samuel Bekele",
      "date_of_birth": "1984-07-14",
      "sex": "male",
      "created_at": "2026-01-01T08:00:00+03:00"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 1,
    "has_more": false
  },
  "meta": {
    "request_id": "req-001"
  }
}
```

### 9.2 Get Patient

```http
GET /api/hospital/v1/patients/{patient_id}
```

Returns the patient resource.

### 9.3 Patient Summary

```http
GET /api/hospital/v1/patients/{patient_id}/summary
```

Purpose: populate the hospital patient overview without requiring many frontend requests.

Example:

```json
{
  "data": {
    "patient_id": "PAT-001",
    "encounter_count": 5,
    "document_count": 12,
    "observation_count": 18,
    "medication_count": 4,
    "imaging_study_count": 1,
    "latest_encounter_at": "2026-02-05T11:20:00+03:00"
  },
  "meta": {
    "request_id": "req-002"
  }
}
```

This endpoint must contain only clinical record counts and metadata, not hidden case insights.

---

# PART II — ENCOUNTERS

## 10. Encounter Resource

```typescript
interface Encounter {
  id: string;
  patient_id: string;
  encounter_type: string;
  department: string;
  provider_name: string;
  started_at: string;
  ended_at: string | null;
  status: string;
}
```

### 10.1 List Patient Encounters

```http
GET /api/hospital/v1/patients/{patient_id}/encounters
```

Filters:

```text
start_at
end_at
department
encounter_type
status
limit
offset
```

Default sort:

```text
started_at DESC, id ASC
```

### 10.2 Get Encounter

```http
GET /api/hospital/v1/encounters/{encounter_id}
```

### 10.3 Encounter Clinical Records

```http
GET /api/hospital/v1/encounters/{encounter_id}/records
```

This is a convenience endpoint for the hospital encounter detail screen.

Example:

```json
{
  "data": {
    "encounter_id": "ENC-001",
    "clinical_event_ids": ["EVT-001"],
    "observation_ids": ["LAB-001"],
    "medication_ids": ["MED-001"],
    "document_ids": ["DOC-001"],
    "diagnosis_ids": ["DX-001"]
  },
  "meta": {
    "request_id": "req-003"
  }
}
```

Return references rather than automatically embedding every full document.

---

# PART III — CLINICAL EVENTS

## 11. Clinical Event Resource

```typescript
interface ClinicalEvent {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  event_type: string;
  occurred_at: string | null;
  documented_at: string | null;
  description: string;
  source_document_id: string | null;
}
```

### 11.1 List Clinical Events

```http
GET /api/hospital/v1/patients/{patient_id}/clinical-events
```

Filters:

```text
event_type
start_at
end_at
encounter_id
limit
offset
```

### 11.2 Get Clinical Event

```http
GET /api/hospital/v1/clinical-events/{event_id}
```

Example:

```json
{
  "data": {
    "id": "EVT-006",
    "patient_id": "PAT-001",
    "encounter_id": "ENC-003",
    "event_type": "symptom",
    "occurred_at": "2026-01-18T14:00:00+03:00",
    "documented_at": "2026-01-22T10:00:00+03:00",
    "description": "Patient-reported onset of a clinical symptom.",
    "source_document_id": "DOC-007"
  },
  "meta": {
    "request_id": "req-004"
  }
}
```

The sample values in this document are illustrative and must not be treated as the actual CASE-001 fixture.

---

# PART IV — DIAGNOSES AND SYMPTOMS

## 12. Diagnosis Resource

```typescript
interface Diagnosis {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  name: string;
  code_system: string | null;
  code: string | null;
  status: string;
  diagnosed_at: string | null;
}
```

### Endpoints

```http
GET /api/hospital/v1/patients/{patient_id}/diagnoses
GET /api/hospital/v1/diagnoses/{diagnosis_id}
```

Diagnosis status must distinguish:

```text
suspected
provisional
confirmed
resolved
historical
ruled_out
```

A provisional diagnosis must never be silently converted into a confirmed diagnosis.

## 13. Symptom Resource

```typescript
interface Symptom {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  name: string;
  onset_at: string | null;
  severity: string | null;
  frequency: string | null;
  status: string;
  description: string | null;
}
```

### Endpoints

```http
GET /api/hospital/v1/patients/{patient_id}/symptoms
GET /api/hospital/v1/symptoms/{symptom_id}
```

Date-only symptom onset values must remain date-only unless a more precise time is supported by the source.

---

# PART V — LABORATORY OBSERVATIONS

## 14. Observation Resource

```typescript
interface Observation {
  id: string;
  patient_id: string;
  encounter_id: string | null;

  test_code: string | null;
  test_name: string;

  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;

  reference_range_low: number | null;
  reference_range_high: number | null;

  status: string;

  specimen_collected_at: string | null;
  reported_at: string | null;

  source_document_id: string | null;
}
```

At least one result value must be present for completed results. Ordered, cancelled, or pending observations may have neither value.

### 14.1 List Observations

```http
GET /api/hospital/v1/patients/{patient_id}/observations
```

Filters:

```text
test_code
test_name
status
encounter_id
start_at
end_at
limit
offset
```

The date range filters use `specimen_collected_at` unless explicitly documented otherwise.

### 14.2 Get Observation

```http
GET /api/hospital/v1/observations/{observation_id}
```

Example:

```json
{
  "data": {
    "id": "LAB-001",
    "patient_id": "PAT-001",
    "encounter_id": "ENC-002",
    "test_code": "HGB",
    "test_name": "Hemoglobin",
    "value_numeric": 10.4,
    "value_text": null,
    "unit": "g/dL",
    "reference_range_low": 12.0,
    "reference_range_high": 17.0,
    "status": "final",
    "specimen_collected_at": "2026-01-20T10:15:00+03:00",
    "reported_at": "2026-01-20T14:20:00+03:00",
    "source_document_id": "DOC-004"
  },
  "meta": {
    "request_id": "req-005"
  }
}
```

### 14.3 Laboratory Series

```http
GET /api/hospital/v1/patients/{patient_id}/observations/series
```

Required parameter:

```text
test_code
```

Optional:

```text
start_at
end_at
```

Response:

```json
{
  "data": {
    "patient_id": "PAT-001",
    "test_code": "HGB",
    "points": [
      {
        "observation_id": "LAB-001",
        "collected_at": "2026-01-20T10:15:00+03:00",
        "value_numeric": 10.4,
        "unit": "g/dL"
      },
      {
        "observation_id": "LAB-009",
        "collected_at": "2026-02-04T09:30:00+03:00",
        "value_numeric": 8.9,
        "unit": "g/dL"
      }
    ]
  },
  "meta": {
    "request_id": "req-006"
  }
}
```

Series results must not combine incompatible units without explicit, validated conversion.

The agent tool `compare_lab_results` performs deterministic comparison above this clinical data layer.

---

# PART VI — MEDICATIONS

## 15. Medication Resource

```typescript
interface Medication {
  id: string;
  patient_id: string;
  encounter_id: string | null;

  medication_name: string;
  generic_name: string | null;

  dose: number | null;
  dose_unit: string | null;
  route: string | null;
  frequency: string | null;

  start_at: string | null;
  end_at: string | null;

  status: string;
  prescriber: string | null;
  ordered_at: string | null;

  source_document_id: string | null;
}
```

### Endpoints

```http
GET /api/hospital/v1/patients/{patient_id}/medications
GET /api/hospital/v1/medications/{medication_id}
```

Filters:

```text
medication_name
status
start_at
end_at
limit
offset
```

### Critical distinction

The API represents medication orders and documented medication history.

An order is not proof of administration or adherence.

The frontend and agent layer must preserve this distinction.

---

# PART VII — CLINICAL DOCUMENTS

## 16. Document Resource

```typescript
interface ClinicalDocument {
  id: string;
  patient_id: string;
  encounter_id: string | null;

  document_type: string;
  title: string;
  author: string | null;

  event_at: string | null;
  authored_at: string | null;

  mime_type: string;
  text_content: string | null;

  has_asset: boolean;
  metadata: Record<string, unknown>;
}
```

The public API must not expose raw server filesystem paths.

### 16.1 List Documents

```http
GET /api/hospital/v1/patients/{patient_id}/documents
```

Filters:

```text
document_type
encounter_id
start_at
end_at
limit
offset
```

Collection responses may omit `text_content` for efficiency.

### 16.2 Search Documents

```http
GET /api/hospital/v1/patients/{patient_id}/documents/search
```

Query:

```text
q
document_type
start_at
end_at
limit
offset
```

Example:

```http
GET /api/hospital/v1/patients/PAT-001/documents/search?q=dizziness
```

Response:

```json
{
  "data": [
    {
      "id": "DOC-003",
      "title": "Primary Care Visit Note",
      "document_type": "progress_note",
      "event_at": "2026-01-12T09:40:00+03:00",
      "snippet": "Patient reports intermittent dizziness...",
      "relevance_score": 0.87
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 1,
    "has_more": false
  },
  "meta": {
    "request_id": "req-007"
  }
}
```

Search ranking must use clinical document content and metadata only.

It must not use ground-truth relevance labels.

### 16.3 Get Document

```http
GET /api/hospital/v1/documents/{document_id}
```

Returns complete document metadata and available extracted text.

### 16.4 Get Document Asset

```http
GET /api/hospital/v1/documents/{document_id}/asset
```

Returns the original PDF or image, if available.

Requirements:

- Enforce authentication and patient authorization.
- Validate the document identifier.
- Resolve storage locations server-side.
- Set the correct `Content-Type`.
- Use safe `Content-Disposition` handling.
- Support browser viewing where appropriate.
- Prevent arbitrary filesystem traversal.
- Return `404` when no asset exists.

Never accept arbitrary filesystem paths from API clients.

---

# PART VIII — DIAGNOSTIC REPORTS

## 17. Diagnostic Report Resource

Diagnostic reports represent finalized or preliminary interpretations of tests and procedures.

```typescript
interface DiagnosticReport {
  id: string;
  patient_id: string;
  encounter_id: string | null;

  report_type: string;
  title: string;

  status: string;
  issued_at: string | null;

  conclusion: string | null;
  document_id: string | null;

  observation_ids: string[];
  imaging_study_id: string | null;
}
```

### Endpoints

```http
GET /api/hospital/v1/patients/{patient_id}/diagnostic-reports
GET /api/hospital/v1/diagnostic-reports/{report_id}
```

Supported report types include:

```text
laboratory
radiology
pathology
cardiology
other
```

The report may reference structured observations, imaging studies, and a source document.

The API must preserve these relationships.

---

# PART IX — IMAGING

## 18. Imaging Study Resource

```typescript
interface ImagingStudy {
  id: string;
  patient_id: string;
  encounter_id: string | null;

  modality: string;
  body_region: string;

  performed_at: string | null;
  reported_at: string | null;

  status: string;
  report_document_id: string | null;
}
```

### Endpoints

```http
GET /api/hospital/v1/patients/{patient_id}/imaging-studies
GET /api/hospital/v1/imaging-studies/{study_id}
GET /api/hospital/v1/imaging-studies/{study_id}/assets
GET /api/hospital/v1/imaging-studies/{study_id}/report
```

### Imaging Asset Resource

```typescript
interface ImagingAsset {
  id: string;
  imaging_study_id: string;
  asset_type: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  metadata: Record<string, unknown>;
}
```

### Asset Retrieval

```http
GET /api/hospital/v1/imaging-assets/{asset_id}/content
```

This endpoint returns authorized binary image content.

### Important distinction

An image asset and a radiology report are separate evidence sources.

The image does not automatically imply the report's interpretation, and the report does not guarantee the synthetic image visually supports every described finding.

Case validation should check that intended image-report relationships are coherent.

The system must not claim that a synthetic illustration is a clinically validated diagnostic image.

---

# PART X — REFERRALS

## 19. Referral Resource

```typescript
interface Referral {
  id: string;
  patient_id: string;
  encounter_id: string | null;

  referring_department: string;
  referred_department: string;

  reason: string;

  ordered_at: string | null;
  appointment_at: string | null;

  status: string;
}
```

### Endpoints

```http
GET /api/hospital/v1/patients/{patient_id}/referrals
GET /api/hospital/v1/referrals/{referral_id}
```

Supported statuses:

```text
ordered
scheduled
completed
cancelled
no_show
unknown
```

Referral records must distinguish an ordered referral from a completed appointment.

---

# PART XI — PATIENT TIMELINE

## 20. Patient Timeline API

```http
GET /api/hospital/v1/patients/{patient_id}/timeline
```

This endpoint provides a deterministic chronological view of available clinical records.

### Query parameters

```text
start_at
end_at
event_types
sort
limit
offset
```

Allowed sort values:

```text
asc
desc
```

### Response

```json
{
  "data": [
    {
      "id": "TL-001",
      "patient_id": "PAT-001",
      "event_type": "encounter",
      "timestamp": "2026-01-12T09:15:00+03:00",
      "timestamp_type": "started_at",
      "title": "Primary Care Visit",
      "description": "Outpatient encounter",
      "source_ref": {
        "type": "encounter",
        "id": "ENC-001"
      }
    },
    {
      "id": "TL-002",
      "patient_id": "PAT-001",
      "event_type": "observation",
      "timestamp": "2026-01-20T10:15:00+03:00",
      "timestamp_type": "specimen_collected_at",
      "title": "Hemoglobin",
      "description": "Laboratory observation",
      "source_ref": {
        "type": "observation",
        "id": "LAB-001"
      }
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 2,
    "has_more": false
  },
  "meta": {
    "request_id": "req-008"
  }
}
```

### Timeline rules

The timeline API:

- Aggregates records.
- Normalizes sortable timestamps.
- Preserves the timestamp type.
- Returns source references.
- Uses stable deterministic ordering.
- Does not identify contradictions.
- Does not infer undocumented clinical events.
- Does not expose hidden evaluation relationships.

The timeline agent may use the same underlying clinical service to reconstruct and analyze chronology.

**The hospital timeline is a factual display. The investigation timeline is an analytical interpretation.**

---

# PART XII — CLINICAL SERVICE CONTRACT

## 21. ClinicalRecordService

The hospital API and agent tools must depend on a common service abstraction.

Recommended Python interface:

```python
from typing import Protocol


class ClinicalRecordService(Protocol):

    async def get_patient(
        self,
        patient_id: str,
    ): ...

    async def list_patients(
        self,
        filters,
    ): ...

    async def get_encounters(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_encounter(
        self,
        encounter_id: str,
    ): ...

    async def get_clinical_events(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_observations(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_medications(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_documents(
        self,
        patient_id: str,
        filters,
    ): ...

    async def search_documents(
        self,
        patient_id: str,
        query: str,
        filters,
    ): ...

    async def get_document(
        self,
        document_id: str,
    ): ...

    async def get_diagnostic_reports(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_imaging_studies(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_referrals(
        self,
        patient_id: str,
        filters,
    ): ...

    async def get_patient_timeline(
        self,
        patient_id: str,
        filters,
    ): ...
```

This is an illustrative interface. The implementation must also cover individual resource retrieval, symptom and diagnosis retrieval, asset metadata, and authorization-aware access.

Use typed Pydantic models or dataclasses rather than untyped dictionaries for production service contracts.

### Implementation

```text
ClinicalRecordService
        |
        +-- SimulatedHospitalService
        |
        +-- FutureFHIRHospitalService
```

The simulated implementation uses SQLite repositories.

The future FHIR implementation may map standardized FHIR resources into the same internal clinical models.

---

## 22. Agent Tool Mapping

The agent tools defined in `agent-tools.md` map to the hospital's clinical service capabilities.

| Agent tool | Clinical service capability | Hospital API equivalent |
|---|---|---|
| `search_patient` | Search patients | `GET /patients` |
| `get_patient` | Get patient | `GET /patients/{id}` |
| `get_encounters` | List encounters | `GET /patients/{id}/encounters` |
| `get_encounter` | Get encounter | `GET /encounters/{id}` |
| `search_clinical_notes` | Search filtered documents | `GET /patients/{id}/documents/search` |
| `get_clinical_note` | Get document | `GET /documents/{id}` |
| `get_lab_results` | List observations | `GET /patients/{id}/observations` |
| `get_lab_result` | Get observation | `GET /observations/{id}` |
| `compare_lab_results` | Deterministic comparison | Built above observation retrieval |
| `get_medication_history` | List medications | `GET /patients/{id}/medications` |
| `get_medication` | Get medication | `GET /medications/{id}` |
| `search_documents` | Search documents | `GET /patients/{id}/documents/search` |
| `get_document` | Get document | `GET /documents/{id}` |
| `get_diagnostic_reports` | List reports | `GET /patients/{id}/diagnostic-reports` |
| `get_diagnostic_report` | Get report | `GET /diagnostic-reports/{id}` |
| `get_imaging_studies` | List studies | `GET /patients/{id}/imaging-studies` |
| `get_imaging_asset_metadata` | Get asset metadata | Via imaging study assets or asset lookup |
| `get_imaging_report` | Get study report | `GET /imaging-studies/{id}/report` |
| `get_referrals` | List referrals | `GET /patients/{id}/referrals` |
| `build_patient_timeline` | Aggregate timeline | `GET /patients/{id}/timeline` |

All paths in this table are relative to `/api/hospital/v1`.

### Important

An agent tool is **not** simply an HTTP client wrapper.

The tool layer additionally provides:

- Agent permission enforcement
- Investigation patient scope
- Input/output validation
- Tool execution auditing
- Source-reference normalization
- Tool-specific result envelopes
- Investigation event emission

---

# PART XIII — PAGINATION AND FILTERING

## 23. Pagination Contract

Collection endpoints use:

```text
limit
offset
```

Defaults:

```text
limit = 20
offset = 0
maximum_limit = 100
```

Pagination response:

```json
{
  "limit": 20,
  "offset": 0,
  "total": 85,
  "has_more": true
}
```

### Deterministic ordering

Every paginated endpoint must have a stable secondary sort key, normally the record ID.

This prevents missing or duplicate records when timestamps are identical.

---

## 24. Filtering Rules

- Unknown query parameters should be rejected when strict validation is enabled.
- Invalid date ranges return `422`.
- `start_at` must not be later than `end_at`.
- Search queries must have configurable length limits.
- Filters must use parameterized repository queries.
- No endpoint may accept raw SQL expressions.
- Filtering must not use ground-truth or red-herring labels.

---

# PART XIV — ASSET STORAGE

## 25. AssetStorage Abstraction

Binary files must be stored separately from clinical metadata.

```text
SQLite
   |
   +-- document metadata
   +-- imaging metadata
   +-- source relationships

Asset Storage
   |
   +-- PDF documents
   +-- scanned prescriptions
   +-- clinical images
   +-- generated imaging assets
```

Recommended interface:

```python
class AssetStorage(Protocol):

    async def exists(
        self,
        asset_key: str,
    ) -> bool: ...

    async def open(
        self,
        asset_key: str,
    ): ...

    async def get_metadata(
        self,
        asset_key: str,
    ): ...
```

### Initial implementation

```text
LocalAssetStorage
```

Future implementation:

```text
S3AssetStorage
```

### Rules

- The client receives resource IDs, not storage paths.
- The backend resolves storage keys.
- Every asset request is authorized.
- MIME types are validated.
- Assets must exist before a case can be marked ready.
- Raw `ground_truth.yaml` and evaluation files are never available through asset storage routes.

---

# PART XV — SIMULATED HOSPITAL DATABASE

## 26. Clinical Tables

The hospital service operates on the clinical domain.

```text
patients
encounters
clinical_events
symptoms
diagnoses
observations
medications
clinical_documents
diagnostic_reports
imaging_studies
imaging_assets
referrals
```

### Relationships

```text
Patient
  |
  +-- Encounters
  |      |
  |      +-- Clinical Events
  |      +-- Symptoms
  |      +-- Diagnoses
  |      +-- Observations
  |      +-- Medications
  |      +-- Documents
  |      +-- Imaging Studies
  |      +-- Referrals
  |
  +-- Diagnostic Reports
```

Every patient-owned resource must be traceable to its patient.

Encounter associations may be nullable when clinically appropriate, but patient ownership must not be ambiguous.

---

## 27. Clinical Data Integrity

Repositories and seed validators must enforce:

- Unique resource IDs
- Valid patient foreign keys
- Valid encounter foreign keys
- Valid source-document references
- Valid imaging-study references
- Valid report-to-observation relationships
- Appropriate timestamp semantics
- Stable record IDs after seeding

### Important distinction

The system must permit **intentional clinical contradictions** in synthetic records.

It must not permit broken database referential integrity.

A contradiction in clinical documentation is valid test data.

A reference to a nonexistent patient is invalid data.

---

# PART XVI — SYNTHETIC CASE SEEDING

## 28. Case Loading Pipeline

The simulated hospital is populated from canonical case fixtures.

```text
cases/CASE-001/
    |
    v
case.yaml + assets
    |
    v
Schema Validation
    |
    v
Referential Validation
    |
    v
Temporal Validation
    |
    v
Asset Validation
    |
    v
Clinical Data Extraction
    |
    v
SQLite
    |
    v
Hospital REST API
```

Ground truth is processed separately:

```text
ground_truth.yaml
    |
    v
Evaluation-only storage
```

### Required scripts

```text
scripts/validate_case.py
scripts/seed_case.py
scripts/seed_all_cases.py
```

### Seed commands

```bash
python scripts/validate_case.py cases/CASE-001
python scripts/seed_case.py cases/CASE-001
python scripts/seed_all_cases.py
```

### Seeding requirements

- Deterministic
- Idempotent
- Transactional
- Validated before commit
- Stable identifiers
- No duplicated records
- Clear errors on invalid references
- No ground-truth leakage

---

# PART XVII — HOSPITAL FRONTEND REQUIREMENTS

## 29. Hospital UI Screens

The hospital frontend should support the following screens.

### 29.1 Patient Directory

Uses:

```http
GET /patients
```

Displays:

- Patient name
- Synthetic MRN
- Demographics
- Patient record link

### 29.2 Patient Overview

Uses:

```http
GET /patients/{id}
GET /patients/{id}/summary
```

Displays:

- Patient header
- Clinical record counts
- Latest encounters
- Navigation to record categories

### 29.3 Encounters

Uses:

```http
GET /patients/{id}/encounters
GET /encounters/{id}
GET /encounters/{id}/records
```

### 29.4 Laboratory Results

Uses:

```http
GET /patients/{id}/observations
GET /patients/{id}/observations/series
```

Displays:

- Test names
- Values and units
- Reference ranges
- Result status
- Collection and reporting timestamps
- Longitudinal trends

### 29.5 Medication History

Uses:

```http
GET /patients/{id}/medications
```

Displays:

- Medication name
- Dose
- Route
- Frequency
- Start/end dates
- Order status

### 29.6 Clinical Documents

Uses:

```http
GET /patients/{id}/documents
GET /documents/{id}
GET /documents/{id}/asset
```

Displays:

- Document list
- Search and filters
- Clinical note viewer
- PDF viewer
- Original document metadata

### 29.7 Imaging

Uses:

```http
GET /patients/{id}/imaging-studies
GET /imaging-studies/{id}/assets
GET /imaging-assets/{id}/content
GET /imaging-studies/{id}/report
```

### 29.8 Patient Timeline

Uses:

```http
GET /patients/{id}/timeline
```

The hospital UI should display raw clinical chronology without automatically revealing the CASETRACE investigation result.

---

# PART XVIII — INVESTIGATION INTEGRATION

## 30. Starting an Investigation

The hospital API does not start investigations.

The investigation API does.

```http
POST /api/investigations
```

Request:

```json
{
  "patient_id": "PAT-001",
  "objective": "Investigate the patient's longitudinal clinical history for inconsistencies and unresolved findings."
}
```

Response:

```json
{
  "investigation_id": "INV-001",
  "status": "queued"
}
```

The frontend then navigates to the investigation workspace.

### Investigation lifecycle

```text
Hospital Patient Record
       |
       | Start Investigation
       v
Investigation API
       |
       v
Investigation Created
       |
       v
Agent Orchestration
       |
       v
Clinical Tools
       |
       v
ClinicalRecordService
       |
       v
Hospital Data
       |
       v
Evidence Verification
       |
       v
Investigation Report
```

---

## 31. Evidence Deep Links

Every verified finding should allow the user to open its original hospital source.

Example evidence reference:

```json
{
  "type": "document",
  "id": "DOC-009"
}
```

Frontend navigation:

```text
/hospital/patients/PAT-001/documents/DOC-009
```

Other supported routes:

```text
/hospital/patients/{patient_id}/encounters/{encounter_id}
/hospital/patients/{patient_id}/labs/{observation_id}
/hospital/patients/{patient_id}/medications/{medication_id}
/hospital/patients/{patient_id}/imaging/{study_id}
```

The frontend must not generate deep links from unsupported or fabricated source IDs.

Source links must resolve to real clinical records.

---

# PART XIX — PERFORMANCE AND RELIABILITY

## 32. Performance Targets

For the hackathon's locally seeded environment, suggested development targets are:

| Operation | Target |
|---|---|
| Patient detail | Under 300 ms |
| Encounter list | Under 500 ms |
| Observation list | Under 500 ms |
| Document metadata | Under 500 ms |
| Document search | Under 1 second |
| Patient timeline | Under 1 second |
| PDF/image asset | Progressive loading |

These are engineering targets, not guaranteed service-level agreements.

Prioritize correctness and reliability over premature optimization.

---

## 33. Database Indexes

Recommended indexes:

```text
patients.synthetic_identifier

encounters.patient_id
encounters.started_at

clinical_events.patient_id
clinical_events.occurred_at

observations.patient_id
observations.test_code
observations.specimen_collected_at

medications.patient_id
medications.ordered_at

clinical_documents.patient_id
clinical_documents.document_type
clinical_documents.event_at

imaging_studies.patient_id
imaging_studies.performed_at

referrals.patient_id
referrals.ordered_at
```

Add composite indexes based on actual query patterns.

---

## 34. Search Implementation

For v1:

- Indexed scalar filtering and bounded text matching are sufficient; introduce SQLite FTS only when a measured requirement justifies it.
- Do not require Elasticsearch.
- Do not require a vector database for basic hospital document search.
- Keep search behavior deterministic and inspectable.
- Return snippets and stable document IDs.

Semantic retrieval may be added later behind the clinical service abstraction.

---

## 35. Caching

Optional caching may be used for:

```text
patient summary
encounter lists
document metadata
timeline aggregation
```

Do not cache authorization decisions across users or scopes.

Do not cache clinical records in a way that leaks one patient's data into another investigation.

---

# PART XX — SECURITY AND CLINICAL SAFETY

## 36. Security Rules

The hospital API must:

- Authenticate requests.
- Enforce authorization for every resource.
- Validate all query parameters.
- Prevent arbitrary SQL execution.
- Prevent filesystem path traversal.
- Restrict asset access.
- Avoid leaking secrets or stack traces.
- Log relevant access events.
- Use synthetic data only.
- Keep evaluation assets outside runtime routes.

### Logging

Audit logs should record:

```text
request_id
actor_id
resource_type
resource_id
action
timestamp
outcome
```

Avoid unnecessarily logging full clinical note contents.

---

## 37. Clinical Safety Rules

The hospital system is a synthetic demonstration environment.

It must not:

- Present synthetic cases as real patients.
- Claim generated medical images are validated diagnostic scans.
- Invent missing clinical values.
- Convert suspected diagnoses into confirmed diagnoses.
- Interpret medication orders as proof of administration.
- Present the investigation system as a substitute for clinical judgment.

The interface should clearly identify the environment as a synthetic clinical simulation.

---

# PART XXI — API IMPLEMENTATION

## 38. Recommended Backend Structure

```text
apps/api/
  app/
    api/
      routes/
        hospital/
          patients.py
          encounters.py
          clinical_events.py
          symptoms.py
          diagnoses.py
          observations.py
          medications.py
          documents.py
          diagnostic_reports.py
          imaging.py
          referrals.py
          timeline.py

    hospital/
      interfaces.py
      simulator.py

      services/
        clinical_record_service.py
        patient_service.py
        encounter_service.py
        observation_service.py
        medication_service.py
        document_service.py
        imaging_service.py
        timeline_service.py

      repositories/
        patient_repository.py
        encounter_repository.py
        observation_repository.py
        medication_repository.py
        document_repository.py
        imaging_repository.py
        referral_repository.py

    schemas/
      hospital/
        common.py
        patient.py
        encounter.py
        clinical_event.py
        observation.py
        medication.py
        document.py
        imaging.py
        referral.py
        timeline.py

    storage/
      interfaces.py
      local.py
```

Keep route handlers thin.

Route handlers should:

1. Validate the request.
2. Authenticate and authorize access.
3. Call the clinical service.
4. Serialize the response.
5. Return appropriate HTTP status codes.

Clinical retrieval logic belongs in services and repositories, not route handlers.

---

## 39. FastAPI Example

```python
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/api/hospital/v1",
    tags=["hospital"],
)


@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    service=Depends(get_clinical_record_service),
    principal=Depends(require_hospital_reader),
):
    patient = await service.get_patient(
        patient_id=patient_id,
        principal=principal,
    )

    return {
        "data": patient,
        "meta": {
            "request_id": get_request_id(),
        },
    }
```

This is illustrative; the production implementation must use typed response models and centrally defined dependencies.

---

# PART XXII — TESTING

## 40. Unit Tests

Test:

- Patient serialization
- Timestamp serialization
- Query validation
- Pagination
- Search filtering
- Empty results
- Missing records
- Invalid IDs
- Source-reference integrity

---

## 41. Integration Tests

Use seeded CASE-001 data.

Verify:

```text
GET /patients/PAT-001
    -> returns patient

GET /patients/PAT-001/encounters
    -> returns seeded encounters

GET /patients/PAT-001/observations
    -> returns correct lab records

GET /documents/DOC-001
    -> returns correct document

GET /documents/DOC-001/asset
    -> returns valid asset when present

GET /patients/PAT-001/timeline
    -> returns deterministic chronology
```

Every result must match the seeded source data.

---

## 42. Security Tests

Verify:

- Unauthenticated requests fail.
- Unauthorized patient access fails.
- Unauthorized document access fails.
- Unauthorized asset access fails.
- Invalid IDs do not expose internals.
- Path traversal attempts fail.
- No ground-truth route exists.
- Ground-truth content does not appear in hospital search results.

---

## 43. Contract Tests

The hospital API and tool layer must agree on:

```text
resource IDs
field names
timestamp semantics
source references
nullability
record statuses
```

Recommended approach:

- Generate OpenAPI from FastAPI.
- Generate frontend TypeScript types from OpenAPI.
- Use shared Pydantic schemas where appropriate.
- Add tests that compare clinical service results with agent tool results.
- Reject contract-breaking changes unless documentation and tests are updated.

---

# PART XXIII — DEVELOPMENT SEQUENCE

## 44. Implementation Phases

### Phase 1 — Clinical Foundation

Build:

```text
SQLite
SQLAlchemy models
Alembic migrations
Case validator
Case seeder
ClinicalRecordService
```

### Phase 2 — Core Hospital API

Build:

```text
Patients
Encounters
Clinical Events
Observations
Medications
Documents
```

### Phase 3 — Multimodal Records

Build:

```text
PDF asset retrieval
Imaging studies
Imaging assets
Diagnostic reports
Referrals
```

### Phase 4 — Timeline and Search

Build:

```text
Patient timeline
Document search
Lab series
Patient summary
```

### Phase 5 — Agent Tool Integration

Connect:

```text
Tool Registry
    |
    v
ClinicalRecordService
    |
    v
Simulated Hospital
```

### Phase 6 — End-to-End CASE-001 Test

Verify the complete flow:

```text
CASE-001
   |
   v
Seed SQLite
   |
   v
Hospital API
   |
   v
Hospital Frontend
   |
   v
Start Investigation
   |
   v
Agent Tools
   |
   v
Retrieve Original Evidence
   |
   v
Verify Contradiction
   |
   v
Evidence-backed Report
```

---

# PART XXIV — DEFINITION OF DONE

## 45. Hospital API Completion Criteria

The hospital API is complete when:

- [ ] All canonical clinical resource endpoints are implemented.
- [ ] CASE-001 can be seeded deterministically.
- [ ] Patient and encounter records are retrievable.
- [ ] Laboratory results preserve values, units, and timestamps.
- [ ] Medication history preserves order and treatment dates.
- [ ] Clinical notes can be searched and retrieved.
- [ ] PDFs and images resolve through authorized endpoints.
- [ ] Diagnostic reports and referrals are linked correctly.
- [ ] Patient timeline is deterministic.
- [ ] Source IDs are stable and traceable.
- [ ] Patient access permissions are enforced.
- [ ] Ground truth is inaccessible through runtime APIs.
- [ ] Agent tools use the clinical service boundary.
- [ ] Hospital frontend uses real API data.
- [ ] Contract tests pass.
- [ ] CASE-001 can be investigated without direct agent database access.

---

# 46. Non-Goals for v1

Do not build:

- A full hospital management system
- Patient registration workflows
- Billing
- Insurance claims
- Appointment scheduling
- Electronic prescribing
- Clinical record editing
- Real patient integrations
- Full FHIR server implementation
- PACS infrastructure
- DICOM ingestion pipelines
- Enterprise hospital administration

These features are outside the hackathon's core objective.

CASETRACE needs a **credible clinical information environment**, not a complete hospital product.

---

# 47. Final Architectural Principle

The simulated hospital must remain independent of the investigation answer.

A normal hospital user sees:

```text
Patient
  |
  +-- Encounters
  +-- Laboratory Results
  +-- Medications
  +-- Clinical Notes
  +-- Diagnostic Reports
  +-- Imaging
  +-- Referrals
```

CASETRACE sees the same clinical records through its tool layer and performs an investigation.

```text
Clinical Records
       |
       v
Agent Tools
       |
       v
Evidence Retrieval
       |
       v
Timeline Reconstruction
       |
       v
Hypothesis Generation
       |
       v
Targeted Verification
       |
       v
Evidence-backed Findings
```

**The hospital provides the evidence.**

**The agents investigate the evidence.**

**The verification engine validates the findings.**

**The frontend makes the investigation understandable.**

That separation is fundamental to CASETRACE's credibility.

---

# 48. Final Rule for Coding Agents

When implementing this API:

> Build it as though the hospital system existed before CASETRACE and CASETRACE is a new investigation product being connected to it.

Do not introduce shortcuts that allow agents to know the mystery in advance.

Do not create endpoints that expose evaluation metadata.

Do not merge hospital responsibilities with agent reasoning.

**The simulated hospital must be realistic enough to investigate, but simple enough to build reliably for the hackathon.**

## Phase 2 implementation status

The implementation uses `/api/hospital/v1` as this contract requires. See
[Phase 2 development](phase-2-development.md) for maintenance commands and
[contract decisions](CONTRACT_DECISIONS.md) for storage mappings and scope.
Phase 1 `/api/health` retains its existing health/error format; hospital errors
use this document's `error` plus `meta.request_id` envelope. No unversioned
hospital aliases or new authentication scheme are introduced. Local demo access
is trusted and is not a claim of production authorization.

Exact substring document search is case-insensitive, ordered by document ID,
and returns relevance_score=1 for every match (unranked retrieval, not evidence
confidence). Lab series refuses mixed units with RESOURCE_CONFLICT rather than
silently converting. Unknown clinical instants remain null; timeline excludes
unknown/date-only event times without replacing them with documentation times.
Assets distinguish unknown records, missing registrations, missing files and
integrity failures. They never reveal server paths or answer keys.

## Refactor 03 timeline compatibility extension

The existing `/api/hospital/v1/patients/{id}/timeline` entries additionally expose
`encounter_id`, `timestamps` (original named temporal values, including null and
date-only strings), and `time_precision: "instant"` for the primary timestamp.
The primary timestamp and timestamp_type retain their prior semantics. Missing
and date-only primary times stay outside this instant-only projection; obtain
them from the original resource endpoint. Other time fields never substitute for
the primary time. Source DTOs and evidence fingerprints remain unchanged.

Case readiness is available to maintenance tooling via
`python -m app.hospital.cli discover CASE-001`. It distinguishes not_present,
invalid, missing_assets, available_not_imported, imported and source_conflict.
Imported means the canonical clinical/asset fingerprint matches persisted state.
This is not a public case-library endpoint. A runtime case catalog still needs
an approved metadata publication contract; raw case files are not runtime inputs.

Refactor 08 also adds optional `q` (1?200 characters) to document collections:
literal case-insensitive title/text matching, combined with encounter/type/clinical
date filters before pagination. Other collections reject nonempty q with 422.
Hospital timeline now applies its declared encounter_id filter to each source's
encounter association (including encounter records themselves). Existing unfiltered
ordering, timestamp projection and source DTOs remain unchanged.
