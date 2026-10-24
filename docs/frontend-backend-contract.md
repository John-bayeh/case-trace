# CASETRACE — Frontend–Backend Contract

Phase 2.5 adds optional nullable `relationship.diagnostic_comparison` to existing
findings and optional nullable `Hypothesis.comparison`. These contain the documented
working hypothesis/certainty, exact source roles/anchors/timestamps, supporting,
weakening and contradictory evidence, missing evidence, alternatives, a question,
provisional_verdict and accessible search manifest. Nonspecific context is marked.
Verdicts are reconsideration_question, not_challenged or inconclusive; existing
Hypothesis.verdict remains inconclusive for generated clinical questions. A verified
finding validates the recorded relationship, not the diagnosis or clinical answer.
Old payloads remain readable. No endpoint, status, SSE or frontend workflow changes.

Phase 2.4 adds optional nullable relationship.result_workflow inside existing
findings/reports: result_id, attribution, search completeness/source manifest and
eleven lifecycle stages with documented/partial/unknown/conflicting states,
original anchors, named timestamps and literal dates. Clients may ignore it.
Administrative closure is independent of completed follow-up and notification.
Existing endpoints, statuses, SSE activity and REST reconciliation remain.

Phase 2.3 adds ClinicalClaim origins `copied_list` and `administration` inside
the optional relationship envelope; administration means documented source
language, not inferred ingestion. The additive `specialist.evidence_requested`
activity event carries requesting/providing agent names, question count, source
references and proposal verification state. Existing routes, finding statuses
and unknown-event tolerance remain unchanged.

## Phase 2.2 additive relationship contract

Candidate/Finding adds optional nullable `relationship` (schema_version 1.0):
relationship_type, constituent ClinicalClaim assertions, supporting/contradicting
assertion IDs, named temporal ordering, unresolved questions and conclusion_kind.
Absent envelopes retain prior behavior. Rule `clinical_relationship` uses existing
finding types and statuses. Existing claim/anchors/alternatives/limitations and
all endpoint paths remain. Reports preserve the envelope in their findings.
SourceRef and Anchor retain their public names and serialized fields.

New SSE activity types are `assertions.extracted`, `relationship.assembled`,
`relationship.proposed` and `relationship.verification_completed`. Payloads carry
bounded IDs/counts/source versions and status, excluding notes and proposed prose.
Unknown event tolerance and REST reconciliation remain required. No frontend
relationship visualization or new route is introduced. See
[relationship architecture](architecture/clinical-relationship-reasoning.md).

## Refactor 09 read-only audit contracts

`GET /api/investigations/{id}/tools?limit=20&offset=0` returns
`{investigation_id, items, total, limit, offset}` ordered by start time then ID.
Items expose persisted tool ID, agent execution ID/name/attempt, tool name/status,
allowlisted scalar arguments, source references, start/completion timestamps,
duration_ms and error_code. Full result payloads are not retained or returned.
Unknown argument keys and nested values are omitted. Missing runs use the shared
404 error. Limits are 1–100; offsets are nonnegative. No execution or schema changes.

Task/lead inspection uses existing ordered persisted events; no private planning
context is exposed. Source verification remains distinct from clinical validity.

Refactor 06 adds optional nullable `char_start`/`char_end` to anchors (zero-based,
end-exclusive Unicode offsets into the original field), and optional default-empty
`alternatives`/`limitations` to hypotheses. Existing anchor fields, endpoint paths,
request shapes, required response fields, status enums and SSE cursors remain.
Clients may ignore these additions. Report execution metadata records `reasoning`.
Offsets, when supplied, must be paired and their original-field slice must equal
the exact quote; no PDF page is inferred. See [evidence contract](evidence-contract.md).

Refactor 05 retains endpoint DTOs/OpenAPI and SSE cursors. Additional activity types:
`plan.created`, `plan.updated`, `plan.stopped`, `task.scheduled`, `task.started`,
`task.assigned`, `task.completed`, `task.failed`, `task.attempt_failed`, `task.skipped`,
`task.cancelled`, `task.rejected`, `lead.identified`, `lead.approved`, `lead.rejected`.
Payloads contain safe task objectives/actions, source identities/versions, dependencies
and results, never private deliberation. Stages can emit `stage.skipped`/`stage.failed`.
REST summarizes repeated agent executions by role; history retains all executions.
Existing report `execution_config` carries strategy and adaptive metrics.

Phase 3 implementation resolution: [phase-3-decisions.md](phase-3-decisions.md)
owns the explicit mapping of older illustrative lifecycle names to the public
enums below. Investigation endpoints are implemented under `/api/investigations`;
hospital endpoints retain `/api/hospital/v1`. POST returns 202 and accepts an
optional `Idempotency-Key`. State adds version, timeline, hypotheses and limitations.
Events add sequence; `after` and numeric `Last-Event-ID` replay committed events.
Findings expose typed anchors, claim_kind, alternatives, limitations,
support_level and verification; `confidence` is not emitted. Anchors use
`source: {type,id}`, source_version/hash, encounter_id, field, expected, quote and
relationship; use the centralized hospital route mapper for source navigation.
Report returns 409 until persisted, then the section 40 shape plus hypotheses and
execution_mode. The API OpenAPI schemas describe all implemented DTOs.

Stack alignment: SQLite + aiosqlite replaces the server database; uv manages Python and pnpm manages the Next.js application. See [development stack](development-stack.md) for path resolution and planned commands. This change does not alter API routes, payloads, IDs, enums or SSE contracts.

**Version:** 1.0  
**Frontend:** Next.js + TypeScript  
**Backend:** FastAPI + Python  
**Transport:** REST + Server-Sent Events (SSE)  
**Purpose:** Contract between the CASETRACE frontend and backend

---

# 1. Purpose

This document defines the API contract between the CASETRACE frontend and backend.

The frontend must be able to:

1. Browse synthetic patients.
2. View a patient's clinical record.
3. Browse encounters, labs, medications, documents, and imaging.
4. Start an investigation.
5. Monitor an investigation in real time.
6. Display agent activity.
7. Display tool activity.
8. Display candidate and verified findings.
9. Open supporting evidence.
10. Display the final investigation report.

The backend must expose these capabilities without requiring the frontend to know anything about:

- SQLAlchemy
- SQLite
- agent internals
- LLM providers
- tool implementation
- orchestration implementation
- ground truth

---

# 2. Architectural Boundary

The frontend communicates only with the public API.

```text
┌───────────────────────────────┐
│          Next.js UI           │
│                               │
│ Patient Workspace             │
│ Clinical Record               │
│ Investigation Dashboard       │
│ Agent Activity                │
│ Evidence Viewer               │
│ Investigation Report          │
└───────────────┬───────────────┘
                │
          REST + SSE
                │
                ▼
┌───────────────────────────────┐
│         FastAPI API           │
│                               │
│ API Routes                    │
│ DTO / Pydantic Schemas        │
│ Investigation Engine          │
│ Clinical Services             │
└───────────────┬───────────────┘
                │
                ▼
        Hospital / Agents
```

The frontend must **never** access the database directly.

---

# 3. API Base URL

Development:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Production:

```env
NEXT_PUBLIC_API_URL=https://api.example.com
```

Frontend API clients should use:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL;
```

Do not hardcode:

```text
localhost:8000
```

inside components.

---

# 4. API Versioning

All public endpoints should be under:

```text
/api
```

Example:

```text
/api/patients
/api/investigations
```

If breaking API changes become necessary, introduce:

```text
/api/v2
```

rather than silently changing existing response contracts.

---

# 5. Identifier Conventions

All resources have stable IDs.

Examples:

```text
Patient:
SYN-001

Encounter:
ENC-001

Document:
DOC-021

Observation:
LAB-009

Medication:
MED-004

Imaging:
IMG-003

Investigation:
INV-001

Finding:
FND-003
```

The frontend must treat IDs as opaque strings.

Do not derive meaning from:

```text
INV-001
```

or parse IDs using string manipulation.

---

# 6. Date and Time Contract

All API timestamps must use ISO 8601.

Example:

```text
2026-10-19T14:32:00Z
```

If timezone information is relevant, it must be explicitly included.

Frontend:

```typescript
type ISODateString = string;
```

Do not assume that timestamps are local browser time.

The backend is responsible for providing canonical timestamps.

---

# 7. Generic API Response Rules

Successful endpoints should return JSON.

Collections should use:

```json
{
  "items": [],
  "total": 0
}
```

unless the endpoint has a documented specialized response.

Example:

```json
{
  "items": [
    {
      "id": "ENC-001",
      "department": "Emergency"
    }
  ],
  "total": 1
}
```

---

# 8. Generic Error Contract

All API errors must follow:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The requested clinical document was not found.",
    "request_id": "req_123"
  }
}
```

Frontend error type:

```typescript
export interface ApiError {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}
```

Common codes:

```text
VALIDATION_ERROR
PATIENT_NOT_FOUND
ENCOUNTER_NOT_FOUND
OBSERVATION_NOT_FOUND
MEDICATION_NOT_FOUND
DOCUMENT_NOT_FOUND
IMAGING_NOT_FOUND
ASSET_NOT_FOUND
INVESTIGATION_NOT_FOUND
INVALID_INVESTIGATION_STATE
AGENT_EXECUTION_FAILED
TOOL_EXECUTION_FAILED
INTERNAL_ERROR
```

The frontend should display `message` to the user where appropriate.

The frontend should use `code` for programmatic behavior.

---

# 9. Patient API

## GET `/api/patients`

Returns available synthetic patients.

### Response

```json
{
  "items": [
    {
      "id": "SYN-001",
      "case_id": "CASE-001",
      "synthetic_identifier": "SYN-001",
      "display_name": "Samuel Bekele",
      "date_of_birth": "1984-05-12",
      "sex": "M"
    }
  ],
  "total": 1
}
```

### TypeScript

```typescript
export interface PatientSummary {
  id: string;
  case_id: string;
  synthetic_identifier: string;
  display_name: string;
  date_of_birth: string;
  sex: string;
}

export interface PatientListResponse {
  items: PatientSummary[];
  total: number;
}
```

---

# 10. GET `/api/patients/{patient_id}`

Returns the complete patient summary.

### Response

```json
{
  "id": "SYN-001",
  "case_id": "CASE-001",
  "synthetic_identifier": "SYN-001",
  "display_name": "Samuel Bekele",
  "date_of_birth": "1984-05-12",
  "sex": "M",
  "summary": {
    "encounter_count": 8,
    "document_count": 17,
    "lab_count": 24,
    "medication_count": 6,
    "imaging_count": 3
  }
}
```

---

# 11. Encounter API

## GET `/api/patients/{patient_id}/encounters`

### Query parameters

```text
from
to
department
encounter_type
```

Example:

```text
/api/patients/SYN-001/encounters?department=Emergency
```

### Response

```json
{
  "items": [
    {
      "id": "ENC-001",
      "patient_id": "SYN-001",
      "encounter_type": "Emergency",
      "department": "Emergency",
      "provider_name": "Dr. Hana Tesfaye",
      "started_at": "2026-03-12T09:10:00Z",
      "ended_at": "2026-03-12T14:20:00Z",
      "status": "completed"
    }
  ],
  "total": 1
}
```

---

# 12. GET `/api/encounters/{encounter_id}`

Returns:

```json
{
  "id": "ENC-001",
  "patient_id": "SYN-001",
  "encounter_type": "Emergency",
  "department": "Emergency",
  "provider_name": "Dr. Hana Tesfaye",
  "started_at": "2026-03-12T09:10:00Z",
  "ended_at": "2026-03-12T14:20:00Z",
  "status": "completed",
  "documents": [],
  "observations": [],
  "medications": []
}
```

The frontend can use this endpoint for the encounter detail view.

---

# 13. Observation API

## GET `/api/patients/{patient_id}/observations`

### Query parameters

```text
test
from
to
encounter_id
status
```

Example:

```text
/api/patients/SYN-001/observations?test=CRP
```

### Response

```json
{
  "items": [
    {
      "id": "LAB-009",
      "patient_id": "SYN-001",
      "encounter_id": "ENC-003",
      "test_code": "CRP",
      "test_name": "C-Reactive Protein",
      "value_numeric": 25.4,
      "value_text": null,
      "unit": "mg/L",
      "reference_low": 0,
      "reference_high": 5,
      "status": "final",
      "specimen_collected_at": "2026-03-18T08:30:00Z",
      "reported_at": "2026-03-18T12:15:00Z",
      "source_document_id": "DOC-031"
    }
  ],
  "total": 1
}
```

---

# 14. Medication API

## GET `/api/patients/{patient_id}/medications`

### Response

```json
{
  "items": [
    {
      "id": "MED-004",
      "patient_id": "SYN-001",
      "encounter_id": "ENC-003",
      "medication_name": "Prednisone",
      "generic_name": "prednisone",
      "dose": 20,
      "dose_unit": "mg",
      "route": "oral",
      "frequency": "once_daily",
      "start_at": "2026-03-18T15:00:00Z",
      "end_at": "2026-03-25T15:00:00Z",
      "status": "active",
      "prescriber": "Dr. Hana Tesfaye",
      "ordered_at": "2026-03-18T14:45:00Z",
      "source_document_id": "DOC-034"
    }
  ],
  "total": 1
}
```

---

# 15. Document API

## GET `/api/patients/{patient_id}/documents`

### Query parameters

```text
document_type
from
to
encounter_id
search
```

### Response

```json
{
  "items": [
    {
      "id": "DOC-021",
      "patient_id": "SYN-001",
      "encounter_id": "ENC-002",
      "document_type": "clinical_note",
      "title": "Emergency Department Note",
      "author": "Dr. Hana Tesfaye",
      "event_at": "2026-03-12T13:00:00Z",
      "authored_at": "2026-03-12T16:30:00Z",
      "mime_type": "text/plain"
    }
  ],
  "total": 1
}
```

---

# 16. GET `/api/documents/{document_id}`

Returns the complete document.

### Response

```json
{
  "id": "DOC-021",
  "patient_id": "SYN-001",
  "encounter_id": "ENC-002",
  "document_type": "clinical_note",
  "title": "Emergency Department Note",
  "author": "Dr. Hana Tesfaye",
  "event_at": "2026-03-12T13:00:00Z",
  "authored_at": "2026-03-12T16:30:00Z",
  "mime_type": "text/plain",
  "text_content": "...",
  "metadata": {},
  "asset": null
}
```

---

# 17. Document Asset Contract

For PDFs and scanned documents:

```json
{
  "asset": {
    "id": "ASSET-014",
    "mime_type": "application/pdf",
    "url": "/api/assets/ASSET-014"
  }
}
```

The frontend should never construct storage paths.

Bad:

```typescript
`/data/assets/${document.id}.pdf`
```

Good:

```typescript
document.asset.url
```

The backend controls asset access.

---

# 18. Imaging API

## GET `/api/patients/{patient_id}/imaging`

### Response

```json
{
  "items": [
    {
      "id": "IMG-003",
      "patient_id": "SYN-001",
      "encounter_id": "ENC-005",
      "modality": "CT",
      "body_region": "Chest",
      "performed_at": "2026-04-02T10:20:00Z",
      "reported_at": "2026-04-02T15:00:00Z",
      "report_document_id": "DOC-045",
      "status": "final"
    }
  ],
  "total": 1
}
```

---

# 19. GET `/api/imaging/{study_id}`

Returns imaging study metadata and report information.

```json
{
  "id": "IMG-003",
  "modality": "CT",
  "body_region": "Chest",
  "performed_at": "2026-04-02T10:20:00Z",
  "reported_at": "2026-04-02T15:00:00Z",
  "report_document_id": "DOC-045",
  "assets": [
    {
      "id": "IMG-ASSET-003",
      "mime_type": "image/png",
      "url": "/api/assets/IMG-ASSET-003"
    }
  ]
}
```

---

# 20. Investigation Lifecycle

An investigation follows:

```text
queued
   ↓
running
   ↓
completed
```

Possible alternative states:

```text
failed
cancelled
completed_with_limitations
```

Frontend status type:

```typescript
export type InvestigationStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_limitations"
  | "failed"
  | "cancelled";
```

---

# 21. Start Investigation

## POST `/api/investigations`

### Request

```json
{
  "patient_id": "SYN-001",
  "objective": "full_record_investigation"
}
```

Optional objective values:

```text
full_record_investigation
timeline_investigation
contradiction_investigation
medication_investigation
laboratory_investigation
```

### Response

```json
{
  "investigation_id": "INV-001",
  "status": "queued",
  "patient_id": "SYN-001",
  "created_at": "2026-10-19T14:00:00Z"
}
```

The frontend should immediately navigate to:

```text
/investigations/INV-001
```

---

# 22. Investigation State

## GET `/api/investigations/{investigation_id}`

### Response

```json
{
  "id": "INV-001",
  "patient_id": "SYN-001",
  "case_id": "CASE-001",
  "objective": "full_record_investigation",
  "status": "running",
  "started_at": "2026-10-19T14:00:02Z",
  "completed_at": null,

  "progress": {
    "current_stage": "contradiction_investigation",
    "completed_stages": 3,
    "total_stages": 5,
    "percent": 60
  },

  "agents": [
    {
      "name": "retrieval",
      "status": "completed"
    },
    {
      "name": "timeline",
      "status": "completed"
    },
    {
      "name": "laboratory",
      "status": "completed"
    },
    {
      "name": "medication",
      "status": "completed"
    },
    {
      "name": "contradiction",
      "status": "running"
    },
    {
      "name": "synthesis",
      "status": "pending"
    }
  ],

  "finding_summary": {
    "proposed": 2,
    "verified": 1,
    "rejected": 0,
    "unresolved": 1
  }
}
```

---

# 23. Agent Status Contract

```typescript
export type AgentStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed";
```

Agent object:

```typescript
export interface AgentStatusInfo {
  name: string;
  status: AgentStatus;
  started_at?: string;
  completed_at?: string;
  tool_calls?: number;
  findings_count?: number;
}
```

Agent names:

```text
retrieval
timeline
laboratory
medication
contradiction
synthesis
```

---

# 24. Investigation Events

## GET `/api/investigations/{investigation_id}/events`

Returns historical events.

```json
{
  "items": [
    {
      "id": "EVT-001",
      "investigation_id": "INV-001",
      "type": "investigation.started",
      "timestamp": "2026-10-19T14:00:02Z",
      "payload": {}
    },
    {
      "id": "EVT-002",
      "investigation_id": "INV-001",
      "type": "agent.started",
      "timestamp": "2026-10-19T14:00:03Z",
      "payload": {
        "agent": "retrieval"
      }
    }
  ],
  "total": 2
}
```

---

# 25. Real-Time Investigation Stream

## GET `/api/investigations/{investigation_id}/stream`

Transport:

```text
text/event-stream
```

Example:

```text
event: agent.started
data: {"agent":"timeline","timestamp":"2026-10-19T14:01:00Z"}

event: tool.started
data: {"agent":"timeline","tool":"get_encounters"}

event: tool.completed
data: {
  "agent":"timeline",
  "tool":"get_encounters",
  "record_count":8
}

event: finding.proposed
data: {
  "finding_id":"FND-001"
}
```

---

# 26. SSE Event Types

Supported event types:

```text
investigation.started
investigation.completed
investigation.failed

agent.started
agent.completed
agent.failed

tool.started
tool.completed
tool.failed

records.retrieved

finding.proposed
finding.verified
finding.rejected

verification.started
verification.completed
```

The frontend must tolerate unknown future event types.

Example:

```typescript
switch (event.type) {
  case "agent.started":
    // handle
    break;

  default:
    // log/ignore
    break;
}
```

Do not crash the investigation UI because a new backend event was introduced.

---

# 27. SSE Event Schema

```typescript
export interface InvestigationEvent {
  id: string;
  investigation_id: string;
  type: InvestigationEventType | string;
  timestamp: string;
  payload: Record<string, unknown>;
}
```

Known event payloads are defined below.

---

# 28. `agent.started`

```json
{
  "agent": "timeline"
}
```

Frontend behavior:

```text
Timeline Agent
● Running
```

---

# 29. `agent.completed`

```json
{
  "agent": "timeline",
  "duration_ms": 8240,
  "findings_count": 2
}
```

Frontend:

```text
Timeline Agent
✓ Completed
2 findings
```

---

# 30. `tool.started`

```json
{
  "agent": "timeline",
  "tool": "get_clinical_notes"
}
```

Frontend should show observable activity:

```text
Timeline Agent
  ↓
Searching clinical notes...
```

Do not display internal model reasoning.

---

# 31. `tool.completed`

```json
{
  "agent": "timeline",
  "tool": "get_clinical_notes",
  "record_count": 8,
  "duration_ms": 412
}
```

Frontend:

```text
Retrieved 8 clinical notes
```

---

# 32. `records.retrieved`

```json
{
  "agent": "retrieval",
  "record_type": "documents",
  "count": 17,
  "source_ids": [
    "DOC-001",
    "DOC-002"
  ]
}
```

The frontend can display:

```text
17 documents discovered
```

---

# 33. Finding Contract

## GET `/api/investigations/{investigation_id}/findings`

### Response

```json
{
  "items": [
    {
      "id": "FND-001",
      "investigation_id": "INV-001",
      "type": "timeline_contradiction",
      "status": "verified",
      "title": "Timeline discrepancy detected",
      "claim": "A laboratory result was documented as reviewed before the specimen was collected.",
      "summary": "The clinical note references LAB-009 during the March 12 encounter, while the source laboratory record shows collection on March 18.",
      "confidence": 0.96,
      "created_at": "2026-10-19T14:02:20Z",
      "verified_at": "2026-10-19T14:02:28Z"
    }
  ],
  "total": 1
}
```

---

# 34. Finding Status

```typescript
export type FindingStatus =
  | "proposed"
  | "verified"
  | "rejected"
  | "unresolved";
```

The UI should make a clear distinction between:

```text
PROPOSED
```

and:

```text
VERIFIED
```

This is critical to CASETRACE's credibility.

---

# 35. Finding Types

Initial types:

```text
timeline_contradiction
laboratory_change
medication_change
documentation_delay
missing_evidence
clinical_relationship
```

Future types can be added without breaking the generic finding UI.

---

# 36. Finding Detail

## GET `/api/investigations/{investigation_id}/findings/{finding_id}`

Response:

```json
{
  "id": "FND-001",
  "type": "timeline_contradiction",
  "status": "verified",
  "title": "Timeline discrepancy detected",
  "claim": "A laboratory result was documented as reviewed before the specimen was collected.",
  "summary": "The March 12 clinical note references a result whose specimen was collected March 18.",
  "confidence": 0.96,

  "sources": [
    {
      "id": "SRC-001",
      "source_type": "document",
      "source_id": "DOC-021",
      "relationship": "supports",
      "label": "Emergency Department Note"
    },
    {
      "id": "SRC-002",
      "source_type": "observation",
      "source_id": "LAB-009",
      "relationship": "contradicts",
      "label": "CRP Laboratory Result"
    }
  ],

  "verification": {
    "status": "verified",
    "checks": [
      {
        "type": "source_existence",
        "status": "passed"
      },
      {
        "type": "date_verification",
        "status": "passed"
      },
      {
        "type": "value_verification",
        "status": "passed"
      }
    ]
  }
}
```

---

# 37. Evidence Source Contract

Every evidence source should contain:

```typescript
export interface EvidenceSource {
  id: string;
  source_type:
    | "patient"
    | "encounter"
    | "observation"
    | "medication"
    | "document"
    | "imaging";

  source_id: string;

  relationship:
    | "supports"
    | "contradicts"
    | "contextualizes"
    | "derived_from";

  label: string;

  locator?: {
    page?: number;
    section?: string;
    line?: number;
  };
}
```

This enables the frontend to build:

```text
Finding
   ↓
Evidence
   ↓
Open original record
```

---

# 38. Evidence Navigation

The frontend must not guess routes.

Backend evidence objects should provide enough information to navigate.

Preferred:

```json
{
  "source_id": "DOC-021",
  "source_type": "document",
  "url": "/api/documents/DOC-021"
}
```

or the frontend may use a centralized route mapper.

Recommended frontend route structure:

```text
/patients/SYN-001
/patients/SYN-001/encounters/ENC-001
/patients/SYN-001/documents/DOC-021
/patients/SYN-001/labs/LAB-009
/patients/SYN-001/imaging/IMG-003
/investigations/INV-001
/investigations/INV-001/findings/FND-001
```

---

# 39. Verification Contract

A verified finding should include explicit verification results.

```typescript
export interface VerificationResult {
  status: "verified" | "rejected" | "inconclusive";

  checks: VerificationCheck[];
}

export interface VerificationCheck {
  type:
    | "source_existence"
    | "value_verification"
    | "date_verification"
    | "document_verification"
    | "relationship_verification"
    | "evidence_completeness";

  status: "passed" | "failed" | "inconclusive";

  message?: string;
}
```

Example UI:

```text
Evidence Verification

✓ Source exists
✓ Timestamp verified
✓ Laboratory value verified
✓ Document reference verified
✓ Timeline relationship verified

VERIFIED
```

---

# 40. Investigation Report

## GET `/api/investigations/{investigation_id}/report`

### Response

```json
{
  "investigation_id": "INV-001",
  "status": "completed",

  "summary": {
    "headline": "A timeline discrepancy was identified across two clinical records.",
    "description": "The investigation found a documented reference to a laboratory result before the underlying specimen collection date."
  },

  "timeline": [],

  "verified_findings": [],

  "rejected_findings": [],

  "unresolved_findings": [],

  "limitations": [
    "The available records do not establish why the documentation discrepancy occurred."
  ],

  "generated_at": "2026-10-19T14:04:00Z"
}
```

---

# 41. Timeline Contract

The timeline UI requires normalized events.

```typescript
export interface TimelineEvent {
  id: string;
  timestamp: string;

  event_type:
    | "encounter"
    | "observation"
    | "medication"
    | "document"
    | "imaging"
    | "clinical_event";

  title: string;
  description?: string;

  source: {
    source_type: string;
    source_id: string;
  };

  timestamps?: {
    occurred_at?: string;
    documented_at?: string;
    reported_at?: string;
  };
}
```

The frontend should display the distinction between:

```text
Occurred
```

and:

```text
Documented
```

when both exist.

This is especially important for CASE-001.

---

# 42. Investigation Progress

The backend provides progress information.

```json
{
  "current_stage": "contradiction_investigation",
  "completed_stages": 3,
  "total_stages": 5,
  "percent": 60
}
```

Frontend should not calculate progress based solely on event count.

The backend is authoritative for investigation progress.

---

# 43. Investigation Stages

Initial stages:

```text
record_discovery
timeline_analysis
laboratory_analysis
medication_analysis
contradiction_investigation
synthesis
```

The frontend can render:

```text
01  Record Discovery        ✓
02  Timeline Analysis       ✓
03  Laboratory Analysis     ✓
04  Medication Analysis     ✓
05  Contradiction Search    ●
06  Final Synthesis         ○
```

---

# 44. Agent Activity UI Contract

The backend exposes only observable agent activity.

Example:

```json
{
  "agent": "contradiction",
  "status": "running",
  "current_action": {
    "type": "tool_execution",
    "tool": "get_lab_result",
    "description": "Retrieving original laboratory record"
  }
}
```

Frontend:

```text
CONTRADICTION INVESTIGATOR

Retrieving original laboratory record...
```

Do not expose:

```text
chain-of-thought
hidden reasoning
internal prompt
raw model response
```

---

# 45. Tool Activity Contract

Tool activity should contain:

```typescript
export interface ToolActivity {
  tool_name: string;
  status: "running" | "completed" | "failed";
  description?: string;
  record_count?: number;
  duration_ms?: number;
}
```

Example:

```text
Retrieval Agent

✓ search_patient
✓ get_encounters
✓ search_documents
✓ get_lab_results

17 documents discovered
24 laboratory results discovered
```

---

# 46. Patient Workspace

The primary patient page should consume:

```text
GET /api/patients/{patient_id}
GET /api/patients/{patient_id}/encounters
GET /api/patients/{patient_id}/observations
GET /api/patients/{patient_id}/medications
GET /api/patients/{patient_id}/documents
GET /api/patients/{patient_id}/imaging
```

Suggested frontend structure:

```text
Patient Workspace
│
├── Patient Header
│
├── Overview
│
├── Timeline
│
├── Encounters
│
├── Labs
│
├── Medications
│
├── Documents
│
├── Imaging
│
└── Investigations
```

---

# 47. Investigation Workspace

Recommended frontend structure:

```text
Investigation Workspace
│
├── Investigation Header
│
├── Progress
│
├── Agent Activity
│
├── Investigation Timeline
│
├── Findings
│
├── Evidence
│
└── Final Report
```

The UI should progressively populate as SSE events arrive.

---

# 48. Investigation Header

Backend data:

```json
{
  "id": "INV-001",
  "patient_id": "SYN-001",
  "status": "running",
  "objective": "full_record_investigation"
}
```

Frontend:

```text
CASE-001
Samuel Bekele

Investigation INV-001

● Investigation in progress
```

---

# 49. Frontend State Model

Recommended state:

```typescript
interface InvestigationState {
  investigation: Investigation | null;

  agents: AgentStatusInfo[];

  events: InvestigationEvent[];

  findings: Finding[];

  activeTools: ToolActivity[];

  report: InvestigationReport | null;

  connection: "connecting" | "connected" | "disconnected";

  error: ApiError | null;
}
```

The frontend should treat backend state as authoritative.

---

# 50. SSE Reconnection

SSE connections can fail.

Frontend behavior:

```text
Connect
   ↓
Receive events
   ↓
Connection lost
   ↓
Reconnect
   ↓
GET /api/investigations/{id}
   ↓
Reconstruct current state
   ↓
Reconnect SSE
```

Never assume that SSE is permanently connected.

---

# 51. Duplicate Events

Events have stable IDs.

Frontend should deduplicate:

```typescript
if (events.has(event.id)) {
  return;
}
```

This prevents duplicate activity when reconnecting.

---

# 52. Event Ordering

The backend event `timestamp` is authoritative for display ordering.

However, the frontend should also preserve the event ID.

If events arrive out of order:

```text
EVT-003
EVT-001
EVT-002
```

the frontend may reorder them by timestamp.

---

# 53. Loading States

Every major resource should support:

```text
idle
loading
success
error
```

Example:

```typescript
interface AsyncState<T> {
  data: T | null;
  status: "idle" | "loading" | "success" | "error";
  error: ApiError | null;
}
```

Do not make the UI assume that data exists immediately.

---

# 54. Empty States

The backend may legitimately return:

```json
{
  "items": [],
  "total": 0
}
```

The frontend should display meaningful empty states.

Examples:

```text
No medications recorded.

No imaging studies found.

No findings have been generated yet.
```

Do not treat empty collections as API failures.

---

# 55. Frontend API Client

Create a centralized API client.

Recommended:

```text
apps/web/
└── lib/
    └── api/
        ├── client.ts
        ├── patients.ts
        ├── encounters.ts
        ├── observations.ts
        ├── medications.ts
        ├── documents.ts
        ├── imaging.ts
        ├── investigations.ts
        └── types.ts
```

Components should not directly call:

```text
fetch("http://localhost:8000/...")
```

Instead:

```typescript
patientsApi.getPatient(patientId);
investigationsApi.start(patientId);
investigationsApi.get(investigationId);
```

---

# 56. API Client Contract

Example:

```typescript
export const investigationsApi = {
  async create(
    request: CreateInvestigationRequest
  ): Promise<CreateInvestigationResponse> {
    // implementation
  },

  async get(
    investigationId: string
  ): Promise<Investigation> {
    // implementation
  },

  async getFindings(
    investigationId: string
  ): Promise<FindingListResponse> {
    // implementation
  },

  async getReport(
    investigationId: string
  ): Promise<InvestigationReport> {
    // implementation
  }
};
```

---

# 57. TypeScript Types

All API response types should live in one shared location.

Example:

```text
lib/api/types.ts
```

or:

```text
lib/api/types/
├── patient.ts
├── encounter.ts
├── observation.ts
├── medication.ts
├── document.ts
├── imaging.ts
├── investigation.ts
├── finding.ts
└── event.ts
```

Do not duplicate API types across components.

---

# 58. Runtime Validation

For important API responses, use runtime validation.

Recommended:

```text
Zod
```

Example:

```typescript
const InvestigationSchema = z.object({
  id: z.string(),
  patient_id: z.string(),
  status: z.enum([
    "queued",
    "running",
    "completed",
    "completed_with_limitations",
    "failed",
    "cancelled"
  ])
});
```

This protects the frontend from silent contract mismatches.

---

# 59. Backend Contract Rule

When a backend schema changes:

```text
Backend schema
      ↓
Update contract
      ↓
Update TypeScript types
      ↓
Update frontend
      ↓
Run integration tests
```

Do not change backend response shapes casually.

---

# 60. Contract Testing

The project should eventually include automated contract tests.

At minimum:

```text
FastAPI response
        ↓
TypeScript/Zod schema
        ↓
Validation
```

Important endpoints:

```text
GET /patients/{id}
GET /patients/{id}/encounters
GET /patients/{id}/observations
GET /patients/{id}/medications
GET /patients/{id}/documents
POST /investigations
GET /investigations/{id}
GET /investigations/{id}/findings
GET /investigations/{id}/report
GET /investigations/{id}/stream
```

---

# 61. Frontend Routes

Recommended Next.js routes:

```text
/
├── patients
│   ├── page.tsx
│   └── [patientId]
│       ├── page.tsx
│       ├── timeline
│       ├── encounters
│       ├── labs
│       ├── medications
│       ├── documents
│       └── imaging
│
└── investigations
    └── [investigationId]
        ├── page.tsx
        └── findings
            └── [findingId]
```

---

# 62. Investigation Creation Flow

Frontend:

```text
User opens patient
        ↓
Clicks "Investigate"
        ↓
POST /api/investigations
        ↓
Backend returns INV-001
        ↓
Frontend navigates to /investigations/INV-001
        ↓
GET investigation state
        ↓
Open SSE connection
        ↓
Render investigation activity
```

---

# 63. Investigation Completion Flow

```text
SSE:
investigation.completed
        ↓
Frontend fetches:
GET /api/investigations/{id}
        ↓
GET /api/investigations/{id}/findings
        ↓
GET /api/investigations/{id}/report
        ↓
Display final investigation
```

Do not rely exclusively on the final SSE event payload for the report.

The report endpoint is authoritative.

---

# 64. Finding Interaction

When the user clicks a finding:

```text
Finding
   ↓
Finding detail
   ↓
Evidence sources
   ↓
Click source
   ↓
Original clinical record
```

Example:

```text
VERIFIED FINDING

Timeline discrepancy detected

Evidence

✓ DOC-021
  Emergency Department Note

↔ LAB-009
  C-Reactive Protein Result

[View clinical note]
[View laboratory result]
```

---

# 65. Evidence Viewer

The evidence viewer should support:

```text
document
laboratory result
medication
encounter
imaging
```

Each evidence type should render using the appropriate component.

Example:

```text
DocumentViewer
LabResultViewer
MedicationViewer
EncounterViewer
ImagingViewer
```

The frontend should not use one generic raw JSON viewer for the primary experience.

---

# 66. Clinical Record vs Investigation Evidence

These are different concepts.

Clinical record:

```text
"What exists in the hospital system?"
```

Investigation evidence:

```text
"What information supports or contradicts an investigation finding?"
```

Do not mix the two models.

The same document can exist in the hospital system and be referenced by multiple investigation findings.

---

# 67. Ground Truth Must Never Reach Frontend

The frontend must never receive:

```text
ground_truth
expected_finding
hidden_contradiction
evaluation_answer
```

during normal investigation.

The UI should discover the mystery through the investigation.

Evaluation-only endpoints, if needed, must be isolated from the normal frontend API.

---

# 68. No Chain-of-Thought Contract

The backend must not send:

```text
agent reasoning
private chain of thought
hidden prompts
raw internal model deliberation
```

The frontend receives only:

```text
observable action
tool used
records retrieved
finding
evidence
verification
final conclusion
```

This keeps the demo understandable and safe.

---

# 69. Recommended Investigation UI Event Sequence

For CASE-001, the expected experience is approximately:

```text
investigation.started

agent.started
  retrieval

tool.started
  search_patient

tool.completed
  patient found

tool.started
  get_encounters

tool.completed
  8 encounters found

agent.completed
  retrieval

agent.started
  timeline

tool.started
  get_clinical_notes

tool.completed
  17 documents retrieved

finding.proposed
  potential timeline discrepancy

agent.completed
  timeline

agent.started
  contradiction

tool.started
  get_document

tool.completed
  DOC-021 retrieved

tool.started
  get_lab_result

tool.completed
  LAB-009 retrieved

verification.started

verification.completed

finding.verified

agent.completed
  contradiction

agent.started
  synthesis

agent.completed
  synthesis

investigation.completed
```

This sequence should feel like the AI is actually investigating the case.

---

# 70. Frontend Display Rules for Agent Events

Use event semantics rather than hardcoded animations.

For example:

```text
agent.started
```

→ show agent as active.

```text
tool.started
```

→ show current action.

```text
tool.completed
```

→ show retrieved information.

```text
finding.proposed
```

→ add finding to investigation stream.

```text
finding.verified
```

→ visually upgrade finding from candidate to verified.

```text
investigation.completed
```

→ reveal final report.

---

# 71. Performance Contract

The backend should paginate large clinical collections.

Example:

```text
GET /api/patients/{id}/documents?page=1&page_size=50
```

Response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 127,
  "has_next": true
}
```

For the hackathon's small synthetic datasets, simple collections are acceptable initially.

---

# 72. Search Contract

Where search is supported:

```text
GET /api/patients/{id}/documents?search=discharge
```

The backend should perform search.

Do not download every document and search them in the browser.

---

# 73. Asset URL Contract

The frontend receives backend-controlled asset URLs.

Example:

```json
{
  "id": "ASSET-001",
  "url": "/api/assets/ASSET-001",
  "mime_type": "application/pdf"
}
```

Frontend:

```typescript
const url = `${API_URL}${asset.url}`;
```

Do not expose:

```text
data/assets/
```

directly to the browser.

---

# 74. Authentication Boundary

For the hackathon, authentication may be minimal.

However, the API should maintain an authentication abstraction.

```text
request
   ↓
authentication dependency
   ↓
current user
   ↓
authorization
   ↓
endpoint
```

The frontend should not assume that authentication will always be absent.

---

# 75. CORS

Development:

```text
http://localhost:3000
```

must be allowed to access:

```text
http://localhost:8000
```

Production origins should be configured through environment variables.

Never use:

```text
allow_origins=["*"]
```

in a production deployment.

---

# 76. Health Endpoint

## GET `/api/health`

Response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected"
}
```

Frontend/admin tooling can use this to detect backend availability.

---

# 77. Frontend Environment Variables

Required:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Optional:

```env
NEXT_PUBLIC_APP_NAME=CASETRACE
```

Do not expose:

```env
LLM_API_KEY
DATABASE_URL
SECRET_KEY
```

through `NEXT_PUBLIC_*`.

Those belong exclusively to the backend.

---

# 78. Backend Environment Variables

Example:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/runtime/casetrace.db
API_HOST=0.0.0.0
API_PORT=8000

LLM_PROVIDER=gemini
LLM_API_KEY=...

FRONTEND_URL=http://localhost:3000

ASSET_STORAGE_PATH=./data/assets
```

The frontend must never receive these values.

---

# 79. API Contract Ownership

### Backend owns

```text
Database schema
Clinical record model
Investigation model
API response schemas
Event schemas
Evidence model
Agent execution
Tool execution
Verification
```

### Frontend owns

```text
UI
Navigation
Visual state
Loading states
SSE connection
Event presentation
User interactions
Client-side caching
```

### Shared contract

```text
Resource IDs
JSON schemas
Enum values
Event types
Error codes
Timestamp format
Pagination format
```

---

# 80. Breaking Change Rules

A breaking change includes:

```text
renaming a JSON field
removing a field
changing a field type
changing an enum value
changing endpoint behavior
changing event structure
```

Before making a breaking change:

```text
1. Update this contract.
2. Update backend schemas.
3. Update frontend types.
4. Update tests.
5. Run end-to-end investigation.
```

---

# 81. API Contract Example — Full Investigation

The complete frontend/backend interaction should look like:

```text
USER
 │
 │ Click "Investigate"
 ▼
POST /api/investigations
 │
 │ { patient_id: "SYN-001" }
 ▼
BACKEND
 │
 │ { investigation_id: "INV-001" }
 ▼
FRONTEND
 │
 │ Navigate
 ▼
/investigations/INV-001
 │
 ├── GET /api/investigations/INV-001
 │
 └── GET /api/investigations/INV-001/stream
             │
             ▼
        SSE EVENTS
             │
             ├── agent.started
             ├── tool.started
             ├── tool.completed
             ├── finding.proposed
             ├── verification.completed
             ├── finding.verified
             └── investigation.completed
                         │
                         ▼
              GET /api/investigations/INV-001/report
                         │
                         ▼
                  FINAL REPORT
```

---

# 82. Definition of Done

The frontend-backend integration is complete when:

## Patient system

- Patients load from the backend.
- Encounters load.
- Labs load.
- Medications load.
- Documents load.
- Imaging loads.
- Clinical documents can be opened.
- Assets can be viewed.

## Investigation

- User can start an investigation.
- Investigation ID is returned immediately.
- Investigation state is persisted.
- Frontend can reconnect to an investigation.
- SSE events stream correctly.
- Agent status updates in real time.
- Tool activity appears in real time.
- Findings appear as they are generated.
- Verified findings are distinguishable from proposed findings.

## Evidence

- Every finding can display its sources.
- Sources can be opened.
- Verification checks can be displayed.
- Timeline events can link back to source records.

## Final report

- Report is retrieved from the backend.
- Verified findings are displayed.
- Rejected findings can be displayed where useful.
- Unresolved findings are displayed.
- Limitations are displayed.
- Evidence links work.

## Reliability

- SSE reconnection works.
- Duplicate events do not corrupt UI state.
- Backend errors have consistent structure.
- Empty data does not break the UI.
- Loading states are handled.
- Failed investigations are represented clearly.

---

# 83. Implementation Order

Build the frontend against the contract in this order:

```text
1. API client
        ↓
2. TypeScript/Zod types
        ↓
3. Patient API
        ↓
4. Patient workspace
        ↓
5. Clinical record viewers
        ↓
6. Investigation creation
        ↓
7. Investigation state
        ↓
8. SSE event system
        ↓
9. Agent activity UI
        ↓
10. Findings UI
        ↓
11. Evidence viewer
        ↓
12. Final report
        ↓
13. Reconnection/recovery
```

Do not start by building the animated agent dashboard.

First make sure the frontend can reliably consume real backend data.

---

# 84. The Core Contract

The most important contract in CASETRACE is:

```text
CLINICAL DATA
     ↓
REST API
     ↓
FRONTEND CLINICAL WORKSPACE


INVESTIGATION
     ↓
REST API
     ↓
INVESTIGATION STATE


LIVE INVESTIGATION
     ↓
SSE
     ↓
AGENT ACTIVITY


FINDING
     ↓
EVIDENCE REFERENCES
     ↓
CLINICAL RECORD


FINAL INVESTIGATION
     ↓
REPORT API
     ↓
FRONTEND
```

The frontend should therefore never need to know **how** CASETRACE found something.

It only needs to know:

> **What happened, what was found, how confident the system is, and what evidence supports it.**

---

# 85. Final Architecture

The completed CASETRACE system should look like:

```text
                    ┌──────────────────────┐
                    │      Next.js         │
                    │                      │
                    │ Patient Workspace    │
                    │ Clinical Timeline    │
                    │ Agent Activity       │
                    │ Findings             │
                    │ Evidence Viewer      │
                    │ Final Report         │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │                      │
                  REST                    SSE
                    │                      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │       FastAPI        │
                    │                      │
                    │ Clinical API         │
                    │ Investigation API    │
                    │ Event API            │
                    └──────────┬───────────┘
                               │
               ┌───────────────┼────────────────┐
               │               │                │
               ▼               ▼                ▼
        Hospital Service   Investigation    Evidence
                            Engine           Engine
               │               │                │
               ▼               ▼                ▼
          SQLite        Agents          Verification
               │
               ▼
       PDFs / Images / Assets
```

The key principle is:

> **REST represents state. SSE represents activity.**

And the most important product principle is:

> **The frontend should show the investigation as an evidence-driven process, not as a chatbot conversation.**

That distinction should remain intact throughout implementation.

## Phase 2 hospital interface alignment

### Phase 4 browser implementation

The browser uses the existing versioned hospital APIs and Phase 3 investigation
DTOs/client, not historical illustrative DTOs below/above. Creation schedules
execution with one POST and a retained Idempotency-Key. Findings, timeline and
hypotheses come from investigation snapshots/results; activity comes from the
ordered persisted events endpoint and SSE replay. No new backend paths were
introduced. Source details resolve through allowlisted hospital resource paths
and are checked against the investigation patient. The source inspector identifies
current source records separately from investigation-time hashes/versions.
See [Phase 4 development](phase-4-development.md) for route and reconnection behavior.

For hospital source data the versioned paths, resource DTOs, pagination and error
envelopes in [hospital-api.md](hospital-api.md) are canonical. Earlier
`/api/patients` examples in architecture documents are historical examples, not
separate runtime endpoints. The frontend uses `lib/api/hospital.ts` and never
loads canonical case files or evaluator keys. Record pages are `/patients` and
`/patients/[patientId]`; their IDs come from the API rather than fixed PAT/SYN
translations. Investigation interface decisions remain gated for Phase 3.

## Refactor 03 compatible hospital timeline metadata

The existing hospital timeline adds optional encounter_id, named timestamps and
primary time_precision (instant). Original resource/source hashes and all existing
fields are unchanged. Date-only and absent primary times remain in the original
resource endpoints. See hospital-api.md for exact behavior. Case discovery is
maintenance-only; a public case-library metadata contract remains deferred.

## Refactor 08 hospital navigation and history

Hospital routes add `/cases`, `/cases/[caseId]`, patient timeline/encounters/labs/medications/documents/imaging subroutes, encounter detail, document detail and patient-scoped source inspection. Existing URLs and source/source_type query keys remain supported. Patient layout shares identity/summary reads. Lists use existing pagination, filters and cancellation; original sources retain ownership checks.

`GET /api/investigations` adds read-only history: `{items,total,limit,offset}` with limit 1?100, offset >=0, optional exact patient_id/case_id/status. Items contain id, patient_id, case_id, objective, status, created_at, nullable started_at/completed_at/current_stage. Persisted rows are ordered created_at descending with ID ties. Status uses existing RunStatus. No tool/event payloads or evaluation fields are included. Existing POST and detail routes are unchanged. Case discovery follows the additive contract in hospital-api.md.

### Additive longitudinal rule and activity metadata

Finding rule `record_series` uses existing finding types and anchor schemas.
It verifies recorded longitudinal observations only. Clients already treat
rule as a string. The activity stream additionally permits `tool.page` and
candidate source_refs/rule/candidate_type fields on finding.proposed; unknown
events remain tolerated. No route, state enum, or database schema changes.
