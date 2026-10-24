# CASETRACE

Refactor 06 adds neutral `app/clinical` claim, concept, temporal, extraction,
comparison, relationship and hypothesis modules. `INVESTIGATION_REASONING=legacy`
remains default; `structured` enables the new bounded rules in both workflow
strategies. Specialists still retrieve through the registry; the verifier
independently resolves sources and reproduces proposition rules. Narrative
anchors use contextual statements and optional exact character offsets.
See [evidence contract](evidence-contract.md) and
[measured reasoning report](refactoring/10-clinical-reasoning-refactor-report.md).

Refactor 05 adds typed tasks/leads, specialist adapters, a planning policy and a
bounded adaptive supervisor beside the default baseline pipeline. See the
[executable multi-agent architecture](multi-agent-architecture.md) and
[implementation report](refactoring/09-multi-agent-refactor-report.md). Clinical
retrieval, verification semantics, provider interface and public endpoints remain.

Refactor 04: the tool registry owns per-tool input schemas, category permissions,
budgets, deadlines, output/provenance validation and durable audit. Document,
laboratory and timeline handlers use the existing ClinicalSource DTO boundary.
No public endpoints or database schemas change. See [tool contracts](agent-tools.md)
and [implementation results](refactoring/08-clinical-tools-refactor-report.md).

R02 implementation: [backend refactor report](refactoring/06-backend-refactor-report.md)
records the current DTO clinical source, simulated adapter, shared evidence rules,
scoped executor, persistence collaborators and composition root. Public contracts,
SQLite schema and deterministic investigation behavior remain unchanged.

The [Refactor 01 audit](refactoring/01-current-state-audit.md) maps these requirements
to actual modules. [Compatibility decisions](refactoring/04-contract-compatibility.md)
identify superseded route/state/DTO examples; [target architecture](refactoring/03-target-architecture.md)
defines proposed boundary improvements without requiring a directory-tree rewrite.

The MVP uses async SQLAlchemy 2.x with aiosqlite, managed by uv. Follow [development stack and SQLite operations](development-stack.md) for centralized absolute paths, WAL, per-connection foreign keys/busy timeout, session lifecycle and bounded write transactions. No session is held across LLM/tool waits; one persistence service owns version-guarded state transitions.

## Backend Architecture & Implementation Specification

**Version:** 1.0
**Backend:** Python + FastAPI
**Database:** SQLite
**Primary purpose:** Synthetic hospital information system + multi-agent clinical investigation engine
**Target:** Hackathon prototype with production-oriented architecture

---

# 1. Backend Mission

The CASETRACE backend is responsible for five things:

1. **Store and serve synthetic hospital records.**
2. **Expose realistic clinical retrieval capabilities through APIs and agent tools.**
3. **Orchestrate multiple specialized investigation agents.**
4. **Track evidence, provenance, verification, and investigation state.**
5. **Stream real investigation activity to the frontend.**

The backend must make the following architecture possible:

```text
                         CASETRACE
                             |
                    Investigation API
                             |
                    Investigation Engine
                             |
              +--------------+--------------+
              |              |              |
         Agent Runtime   Evidence Engine   Audit
              |
      +-------+--------+--------+--------+
      |       |        |        |        |
   Timeline  Labs   Medication  Contradiction
    Agent   Agent     Agent       Agent
      |       |        |        |
      +-------+--------+--------+
              |
         Tool Registry
              |
      Clinical Tool Layer
              |
     Hospital Data Adapter
              |
      Simulated Hospital
              |
        SQLite
              +
      Clinical Documents
      PDF / Images / Assets
```

The critical boundary is:

**Agents never access the database directly.**

They interact with clinical information through defined tools.

This is important because the eventual real system should be able to replace:

```text
SimulatedHospitalAdapter
```

with:

```text
FHIRHospitalAdapter
```

without rewriting the investigation engine.

---

# 2. Architectural Principles

## 2.1 Hospital data and investigation data are separate

The synthetic hospital is the source of clinical records.

The investigation system creates a separate representation of:

- retrieved records
- evidence
- findings
- hypotheses
- verification results
- agent activity
- final reports

Agents should never modify the underlying patient record.

---

## 2.2 Agents do not receive the whole case

Do not pass CASE-001.json directly into an LLM.

Instead:

```text
Agent
  ↓
Tool
  ↓
Hospital API/service
  ↓
Relevant records
  ↓
Agent
```

This creates the realistic behavior we want to demonstrate.

---

## 2.3 Ground truth is isolated

The synthetic case generator knows the ground truth.

The evaluation system knows the ground truth.

The agents do not.

The hospital API does not.

The frontend does not.

The production investigation runtime must have no route through which an agent can request:

```text
GET /ground-truth/CASE-001
```

There should effectively be two worlds:

```text
CASE DATA
    ↓
Hospital system
    ↓
Agents

GROUND TRUTH
    ↓
Evaluation engine
```

---

## 2.4 LLMs propose; deterministic systems verify

LLMs are excellent for:

- extracting information from narrative notes
- generating investigative hypotheses
- connecting semantic relationships
- summarizing evidence
- identifying potentially relevant records

They should not be trusted blindly for:

- timestamps
- numerical laboratory values
- medication dates
- source IDs
- document references
- evidence existence

Whenever possible:

```text
LLM proposes
       ↓
Python verifies
       ↓
Evidence engine confirms/rejects
```

---

# 3. Technology Stack

## Core

| Layer           | Technology         |
| --------------- | ------------------ |
| Language        | Python 3.12+       |
| API             | FastAPI            |
| Validation      | Pydantic v2        |
| ORM             | SQLAlchemy 2       |
| Database        | SQLite         |
| Migrations      | Alembic            |
| Async execution | asyncio            |
| Streaming       | Server-Sent Events |
| HTTP client     | httpx              |
| Testing         | pytest             |
| Containers      | Docker Compose     |

## AI

Use a provider-independent model interface.

```text
LLMProvider
    |
    +── GeminiProvider
    +── OpenAIProvider
    +── AnthropicProvider
    +── LocalProvider
```

The agent layer should never directly depend on a specific provider SDK.

---

# 4. Repository Structure

```text
apps/
└── api/
    ├── app/
    │   ├── main.py
    │   │
    │   ├── api/
    │   │   ├── routes/
    │   │   │   ├── cases.py
    │   │   │   ├── patients.py
    │   │   │   ├── encounters.py
    │   │   │   ├── observations.py
    │   │   │   ├── medications.py
    │   │   │   ├── documents.py
    │   │   │   ├── imaging.py
    │   │   │   ├── investigations.py
    │   │   │   └── health.py
    │   │   └── dependencies.py
    │   │
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   ├── logging.py
    │   │   ├── errors.py
    │   │   └── security.py
    │   │
    │   ├── models/
    │   │   ├── patient.py
    │   │   ├── encounter.py
    │   │   ├── observation.py
    │   │   ├── medication.py
    │   │   ├── document.py
    │   │   ├── imaging.py
    │   │   ├── investigation.py
    │   │   ├── evidence.py
    │   │   └── audit.py
    │   │
    │   ├── schemas/
    │   │   ├── patient.py
    │   │   ├── encounter.py
    │   │   ├── observation.py
    │   │   ├── medication.py
    │   │   ├── document.py
    │   │   ├── investigation.py
    │   │   ├── evidence.py
    │   │   └── events.py
    │   │
    │   ├── hospital/
    │   │   ├── interfaces.py
    │   │   ├── simulator.py
    │   │   ├── repositories/
    │   │   └── services/
    │   │
    │   ├── agents/
    │   │   ├── base.py
    │   │   ├── retrieval.py
    │   │   ├── timeline.py
    │   │   ├── laboratory.py
    │   │   ├── medication.py
    │   │   ├── contradiction.py
    │   │   └── synthesis.py
    │   │
    │   ├── tools/
    │   │   ├── registry.py
    │   │   ├── patient_tools.py
    │   │   ├── encounter_tools.py
    │   │   ├── laboratory_tools.py
    │   │   ├── medication_tools.py
    │   │   ├── document_tools.py
    │   │   └── imaging_tools.py
    │   │
    │   ├── orchestration/
    │   │   ├── engine.py
    │   │   ├── state.py
    │   │   ├── tasks.py
    │   │   ├── policies.py
    │   │   └── events.py
    │   │
    │   ├── evidence/
    │   │   ├── collector.py
    │   │   ├── verifier.py
    │   │   ├── graph.py
    │   │   └── provenance.py
    │   │
    │   ├── llm/
    │   │   ├── interface.py
    │   │   ├── providers/
    │   │   ├── prompts/
    │   │   └── structured.py
    │   │
    │   ├── evaluation/
    │   │   ├── ground_truth.py
    │   │   ├── evaluator.py
    │   │   └── metrics.py
    │   │
    │   └── workers/
    │       └── investigation_worker.py
    │
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   ├── agents/
    │   ├── tools/
    │   ├── hospital/
    │   └── investigations/
    │
    ├── alembic/
    ├── pyproject.toml
    └── Dockerfile
```

---

# 5. Database Architecture

SQLite is the system of record.

The database should contain two logical domains.

## Clinical domain

```text
patients
encounters
clinical_events
observations
medications
clinical_documents
diagnostic_reports
imaging_studies
imaging_assets
referrals
```

## Investigation domain

```text
investigations
investigation_events
agent_runs
tool_executions
evidence_items
findings
finding_sources
verification_results
investigation_reports
```

Ground-truth tables should be isolated from ordinary application access.

---

# 6. Clinical Data Model

## Patient

```text
patients
---------
id
case_id
synthetic_identifier
display_name
date_of_birth
sex
created_at
```

The frontend should primarily use the synthetic identifier.

Example:

```text
Patient ID: SYN-001
```

---

# 7. Encounter Model

```text
encounters
----------
id
patient_id
encounter_type
department
provider_name
started_at
ended_at
status
created_at
```

Examples:

```text
Emergency
Outpatient
Radiology
Specialist consultation
Hospital admission
Follow-up
Referral
```

---

# 8. Clinical Event Model

The event model is particularly important for CASETRACE.

```text
clinical_events
---------------
id
patient_id
encounter_id
event_type
occurred_at
documented_at
source_document_id
description
```

The distinction between:

```text
occurred_at
```

and:

```text
documented_at
```

must be preserved.

This is one of the mechanisms through which the timeline contradiction can emerge naturally.

---

# 9. Observation Model

```text
observations
------------
id
patient_id
encounter_id
test_code
test_name
value_numeric
value_text
unit
reference_low
reference_high
status
specimen_collected_at
reported_at
source_document_id
```

Never store only a formatted string such as:

```text
"CRP: 25 mg/L"
```

Store the structured components separately.

This allows CASETRACE to perform real longitudinal analysis.

---

# 10. Medication Model

```text
medications
-----------
id
patient_id
encounter_id
medication_name
generic_name
dose
dose_unit
route
frequency
start_at
end_at
status
prescriber
ordered_at
source_document_id
```

Important distinction:

```text
Medication ordered
≠
Medication taken
```

The data model must preserve this distinction.

---

# 11. Document Model

All clinical documents should share a common abstraction.

```text
clinical_documents
------------------
id
patient_id
encounter_id
document_type
title
author
event_at
authored_at
mime_type
storage_path
text_content
metadata_json
created_at
```

Supported document types:

```text
clinical_note
consultation_note
prescription
laboratory_report
radiology_report
referral
discharge_summary
encounter_summary
scanned_document
```

Large binary files should not be stored directly inside SQLite.

Store:

```text
metadata + storage reference
```

instead.

---

# 12. Imaging Model

```text
imaging_studies
---------------
id
patient_id
encounter_id
modality
body_region
performed_at
reported_at
report_document_id
status
```

And:

```text
imaging_assets
--------------
id
study_id
asset_type
storage_path
mime_type
width
height
metadata_json
```

For the hackathon, assets can live in:

```text
data/assets/
```

Later this can become an object-storage adapter.

---

# 13. Hospital Service Abstraction

The investigation engine should never directly depend on SQLAlchemy models.

Define a clinical information interface.

```python
class ClinicalRecordService(Protocol):

    async def get_patient(
        self,
        patient_id: str
    ) -> PatientRecord:
        ...

    async def get_encounters(
        self,
        patient_id: str
    ) -> list[EncounterRecord]:
        ...

    async def get_observations(
        self,
        patient_id: str,
        filters: ObservationFilters | None = None
    ) -> list[ObservationRecord]:
        ...

    async def get_medications(
        self,
        patient_id: str
    ) -> list[MedicationRecord]:
        ...

    async def get_documents(
        self,
        patient_id: str,
        document_type: str | None = None
    ) -> list[DocumentRecord]:
        ...

    async def get_document(
        self,
        document_id: str
    ) -> DocumentRecord:
        ...
```

Implementation:

```text
ClinicalRecordService
        |
        +── SimulatedHospitalService
        |
        +── FHIRHospitalService (future)
        |
        +── OtherHospitalAdapter (future)
```

This abstraction is strategically important.

---

# 14. Hospital API

The simulated hospital should expose APIs that resemble a real clinical information environment.

## Patient

```http
GET /api/patients
GET /api/patients/{patient_id}
```

## Encounters

```http
GET /api/patients/{patient_id}/encounters
GET /api/encounters/{encounter_id}
```

## Observations

```http
GET /api/patients/{patient_id}/observations
```

Query parameters:

```text
test
from
to
encounter_id
```

## Medications

```http
GET /api/patients/{patient_id}/medications
```

## Documents

```http
GET /api/patients/{patient_id}/documents
GET /api/documents/{document_id}
```

## Imaging

```http
GET /api/patients/{patient_id}/imaging
GET /api/imaging/{study_id}
GET /api/imaging/{study_id}/assets
```

The hospital APIs are what the frontend uses to simulate ordinary hospital software.

The agents should use the **tool layer**, which internally calls these services.

---

# 15. Agent Tool Architecture

This is one of the most important parts of CASETRACE.

Agents receive a restricted toolset.

Example:

```python
Tool(
    name="get_patient_encounters",
    description="Retrieve encounters for a patient.",
    input_schema=...,
    handler=...
)
```

Tools should have:

- Name.
- Description.
- Input schema.
- Permission scope.
- Handler.
- Output schema.
- Audit logging.

---

# 16. Core Tools

## Patient tools

```text
search_patient
get_patient
```

## Encounter tools

```text
get_encounters
get_encounter
```

## Clinical note tools

```text
search_clinical_notes
get_clinical_note
```

## Laboratory tools

```text
get_lab_results
get_lab_result
compare_lab_results
```

## Medication tools

```text
get_medication_history
get_medication
```

## Diagnostic tools

```text
get_diagnostic_reports
get_diagnostic_report
```

## Imaging tools

```text
get_imaging_studies
get_imaging_asset_metadata
get_imaging_report
```

## Document tools

```text
search_documents
get_document
```

The tools should return structured data plus provenance.

---

# 17. Tool Result Contract

A tool should not simply return:

```json
{
  "data": [...]
}
```

Instead:

```json
{
  "status": "success",
  "records": [...],
  "source_refs": [
    {
      "record_id": "LAB-001",
      "document_id": "DOC-014"
    }
  ],
  "retrieved_at": "2026-10-19T..."
}
```

The agent needs both:

```text
information
+
where the information came from
```

This makes evidence tracking much easier.

---

# 18. Agent Architecture

All agents implement a common interface.

```python
class InvestigationAgent(Protocol):

    name: str

    async def run(
        self,
        context: InvestigationContext
    ) -> AgentResult:
        ...
```

Every agent receives a controlled context.

The context contains:

```text
investigation ID
patient ID
investigation objective
available evidence
previous findings
tool permissions
workflow state
```

It does not contain hidden ground truth.

---

# 19. Agent 1 — Retrieval Agent

Purpose:

**Discover what information exists.**

Workflow:

```text
Patient ID
   ↓
search patient
   ↓
retrieve encounters
   ↓
identify record categories
   ↓
retrieve relevant documents
   ↓
create record manifest
```

Output:

```text
RecordManifest
```

Containing:

- Encounters found.
- Documents found.
- Lab records found.
- Medication records found.
- Imaging records found.
- Missing categories.
- Source IDs.

The Retrieval Agent should not attempt to solve the medical mystery.

Its job is discovery.

---

# 20. Agent 2 — Timeline Agent

Input:

```text
retrieved encounters
clinical events
clinical notes
medications
observations
diagnostic reports
```

Responsibilities:

- Normalize timestamps.
- Order events.
- Identify ambiguous dates.
- Detect chronology conflicts.
- Generate candidate timeline findings.

Output:

```text
TimelineFinding
```

Example:

```text
Potential discrepancy:

Clinical note DOC-021 states that laboratory result LAB-009
was reviewed during the March 12 encounter.

LAB-009 source metadata indicates specimen collection on
March 18.

Status: candidate contradiction.
```

The agent should not immediately call this a definitive error.

It should send it to verification.

---

# 21. Agent 3 — Laboratory Agent

Responsibilities:

- Analyze longitudinal laboratory results.
- Detect meaningful changes.
- Check units.
- Associate results with encounters.
- Identify missing measurements.
- Generate evidence-backed observations.

Example output:

```text
Finding:
CRP increased from X to Y between DATE-A and DATE-B.

Sources:
LAB-003
LAB-007

Status:
proposed
```

The deterministic layer should validate that the actual values exist.

---

# 22. Agent 4 — Medication Agent

Responsibilities:

- Reconstruct medication history.
- Detect medication changes.
- Compare medication exposure against symptom documentation.
- Identify discrepancies between prescription and reconciliation records.

The agent should use careful language.

Bad:

```text
Medication caused the patient's symptoms.
```

Better:

```text
Symptoms were documented after the medication was recorded
as started. The available records do not establish causality.
```

This distinction matters enormously in a healthcare demo.

---

# 23. Agent 5 — Contradiction Investigator

This is the **hero agent** for CASE-001.

Input:

```text
candidate contradiction
```

It then performs targeted retrieval.

Example:

```text
Candidate:
DOC-021 conflicts with LAB-009.

        ↓

Retrieve DOC-021
        ↓
Retrieve LAB-009
        ↓
Retrieve associated encounter
        ↓
Retrieve original laboratory metadata
        ↓
Compare timestamps
        ↓
Check whether delayed documentation explains discrepancy
        ↓
Classify
```

Possible outputs:

```text
VERIFIED_CONTRADICTION
DOCUMENTATION_DELAY
AMBIGUOUS
FALSE_POSITIVE
INSUFFICIENT_EVIDENCE
```

This agent is where CASETRACE becomes more than a summarization system.

---

# 24. Agent 6 — Synthesis Agent

The synthesis agent should not blindly trust other agents.

It receives:

```text
verified findings
rejected findings
unresolved findings
evidence graph
timeline
limitations
```

Then produces:

```text
InvestigationReport
```

The report should contain:

```text
Summary
Timeline
Verified Findings
Supporting Evidence
Conflicting Evidence
Unresolved Questions
Limitations
Source References
```

---

# 25. Investigation State

Persist investigation state in SQLite.

```text
investigations
--------------
id
patient_id
case_id
status
objective
started_at
completed_at
created_by
error
```

The investigation itself should be recoverable after a server restart.

---

# 26. Agent Run Model

```text
agent_runs
----------
id
investigation_id
agent_name
status
started_at
completed_at
input_snapshot
output_snapshot
error
```

Do not store chain-of-thought.

Store:

- task
- observable actions
- structured output
- evidence references
- errors

---

# 27. Tool Execution Model

```text
tool_executions
---------------
id
investigation_id
agent_run_id
tool_name
arguments_json
status
started_at
completed_at
result_summary
source_refs_json
error
```

This allows the frontend to display:

```text
Timeline Agent
    ↓
get_clinical_notes()
    ↓
8 records retrieved
    ↓
Candidate discrepancy detected
```

without exposing private model reasoning.

---

# 28. Investigation Event Bus

Every important backend operation should generate a typed event.

```text
investigation.started

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

investigation.completed
investigation.failed
```

Event structure:

```python
class InvestigationEvent(BaseModel):
    id: str
    investigation_id: str
    type: str
    timestamp: datetime
    payload: dict
```

Events should be persisted.

Then broadcast through SSE.

---

# 29. SSE Architecture

Frontend:

```text
GET /api/investigations/{id}/events
```

Backend:

```text
SQLite
     ↓
Investigation Event Service
     ↓
SSE stream
     ↓
Next.js
```

Do not make SSE the only source of state.

The frontend should be able to reconnect and retrieve:

```text
GET /api/investigations/{id}
```

and reconstruct the current state.

---

# 30. Orchestration Engine

The orchestrator controls the investigation lifecycle.

Conceptually:

```python
async def investigate(patient_id):

    investigation = create_investigation()

    await retrieval_agent.run()

    results = await asyncio.gather(
        timeline_agent.run(),
        laboratory_agent.run(),
        medication_agent.run()
    )

    candidates = collect_candidate_findings(results)

    verified = []

    for candidate in candidates:
        result = await contradiction_agent.verify(candidate)
        verified.append(result)

    report = await synthesis_agent.run(
        verified_findings=verified
    )

    return report
```

This is deliberately simple.

The first version should not create an unrestricted autonomous agent swarm.

---

# 31. Why Controlled Orchestration

For the hackathon, reliability matters more than theoretical autonomy.

We want:

```text
predictable workflow
+
real tool usage
+
specialized agents
+
targeted autonomy
```

rather than:

```text
six LLMs talking endlessly to each other
```

The orchestrator should determine:

- Which agents run.
- When they run.
- What tools they can access.
- When additional retrieval is justified.
- When verification is mandatory.
- When the investigation terminates.

---

# 32. Evidence System

The evidence system is the backbone of trust.

Every finding should be connected to source records.

```text
Finding
   |
   +── supports → Document
   |
   +── supports → Observation
   |
   +── conflicts → Document
   |
   +── relates_to → Encounter
```

Represent this with:

```text
evidence_items
--------------
id
investigation_id
type
claim
status
created_by
created_at
```

and:

```text
finding_sources
---------------
finding_id
source_type
source_id
relationship
locator
```

Relationships:

```text
supports
contradicts
contextualizes
derived_from
```

---

# 33. Deterministic Evidence Verification

Implement a verification service independent of the LLM.

For every finding:

### Source existence

Does the referenced record exist?

### Value verification

Does the claimed lab value match the source?

### Date verification

Does the claimed date match the source?

### Document verification

Does the quoted or referenced section actually exist?

### Relationship verification

Does the timeline relationship follow from the underlying timestamps?

### Evidence completeness

Does every important claim have at least one source?

Example:

```python
verification = verify_finding(finding)

if verification.valid:
    finding.status = "verified"
else:
    finding.status = "rejected"
```

This system should be heavily unit-tested.

---

# 34. Evidence Graph

For the hackathon, implement a lightweight relational evidence graph rather than introducing a graph database immediately.

Example:

```text
Encounter E-003
      |
      +── produced → Note N-012
      |
      +── produced → Lab L-004
      |
      +── associated → Medication M-002

Finding F-003
      |
      +── supported_by → N-012
      +── contradicted_by → L-004
```

If the product grows later, this graph abstraction can move to a dedicated graph database.

---

# 35. Document Storage

Separate structured data from binary artifacts.

```text
SQLite
    |
    +── metadata
    +── relationships
    +── timestamps
    +── extracted text

File/object storage
    |
    +── PDFs
    +── synthetic images
    +── scanned documents
```

Hackathon:

```text
data/assets/
```

Production:

```text
S3-compatible object storage
```

Create a storage abstraction:

```python
class AssetStorage(Protocol):

    async def get(self, asset_id: str) -> BinaryIO:
        ...

    async def put(self, asset: BinaryIO) -> str:
        ...
```

---

# 36. Synthetic Case Loading

CASE-001 through CASE-010 should be imported through a controlled seed process.

Example:

```text
scripts/
    validate_case.py
    seed_case.py
    seed_all_cases.py
```

Workflow:

```text
Case files
   ↓
Schema validation
   ↓
Reference validation
   ↓
Temporal consistency checks
   ↓
Asset validation
   ↓
Database seed
```

A case should never enter the hospital database if its references are broken.

---

# 37. Case Validation

The backend should validate:

### Referential integrity

Every:

```text
encounter_id
document_id
patient_id
source_document_id
imaging_study_id
```

must resolve.

### Temporal integrity

Check:

```text
specimen time <= report time
encounter start <= encounter end
medication start/end consistency
```

unless the case intentionally contains a discrepancy.

### Artifact integrity

Every declared PDF/image/document must exist.

### Ground-truth integrity

The evaluator should verify that intended contradictions actually exist.

This is extremely important.

We don't want to discover during the demo that CASE-001's "contradiction" isn't actually contradictory.

---

# 38. Ground Truth and Evaluation

Create a separate evaluation module.

```text
evaluation/
├── ground_truth.py
├── evaluator.py
└── metrics.py
```

The evaluator can compare:

```text
Agent finding
      ↓
Ground truth
```

Metrics:

- Finding recall.
- Evidence precision.
- Source citation accuracy.
- Timeline accuracy.
- False-positive contradiction rate.
- Unsupported-claim rate.

This module must never be exposed to the normal agent runtime.

---

# 39. LLM Abstraction

Define:

```python
class LLMProvider(Protocol):

    async def generate(
        self,
        messages: list[Message],
        response_schema: type[BaseModel],
        tools: list[ToolDefinition] | None = None
    ) -> BaseModel:
        ...
```

Agents interact with this interface.

Example:

```text
TimelineAgent
     |
     v
LLMProvider
     |
     +── Gemini
     +── Claude
     +── OpenAI
```

Changing model providers should not require rewriting the agents.

---

# 40. Structured Outputs

Every agent should return validated Pydantic models.

Example:

```python
class TimelineDiscrepancy(BaseModel):
    claim: str
    event_a_id: str
    event_b_id: str
    reason: str
    source_ids: list[str]
    confidence: float
```

Never rely on parsing arbitrary natural-language responses.

---

# 41. Prompt Architecture

Prompts should live separately from Python business logic.

```text
llm/prompts/
├── retrieval/
├── timeline/
├── laboratory/
├── medication/
├── contradiction/
└── synthesis/
```

Each agent prompt should define:

```text
ROLE
OBJECTIVE
AVAILABLE EVIDENCE
AVAILABLE TOOLS
CONSTRAINTS
OUTPUT SCHEMA
SAFETY RULES
```

Agents should be explicitly instructed:

- Do not invent records.
- Do not invent dates.
- Do not invent values.
- Do not claim causality without evidence.
- Cite source IDs.
- Mark uncertainty.
- Request additional evidence when necessary.

---

# 42. Error Handling

Agent systems fail differently from normal APIs.

Handle:

```text
LLM timeout
LLM malformed response
tool timeout
database failure
missing document
invalid source reference
agent loop
SSE disconnect
partial investigation
```

Every investigation should have a recoverable state.

For example:

```text
Agent 1 ✓
Agent 2 ✓
Agent 3 ✓
Agent 4 ✗

Investigation:
COMPLETED_WITH_LIMITATIONS
```

Do not throw away successful evidence merely because one specialist failed.

---

# 43. Agent Guardrails

Set limits:

```text
max investigation duration
max agent iterations
max tool calls per agent
max tokens per agent
max concurrent agents
```

Example:

```text
Retrieval Agent:
maximum 30 tool calls

Contradiction Agent:
maximum 10 targeted retrieval calls

Synthesis Agent:
no retrieval tools
```

The synthesis agent should generally consume verified evidence rather than independently searching the hospital system.

---

# 44. Permissions Model

Even in the simulated environment, define tool scopes.

Example:

```text
Retrieval Agent
    patient.read
    encounter.read
    document.read
    observation.read
    medication.read

Timeline Agent
    encounter.read
    document.read
    observation.read

Medication Agent
    medication.read
    document.read

Contradiction Agent
    document.read
    observation.read
    encounter.read

Synthesis Agent
    investigation.read
    evidence.read
```

This makes the architecture much closer to a real healthcare AI platform.

---

# 45. Security Architecture

The hackathon contains synthetic data, but design as though the system will eventually process PHI.

Implement:

- API authentication abstraction.
- Role/permission abstraction.
- Audit logging.
- Input validation.
- Safe document rendering.
- No secrets in source code.
- No hidden ground truth in API responses.
- Controlled asset access.
- Structured logging without unnecessary patient content.
- Environment-specific configuration.

Future production requirements would include real identity management, authorization, encryption, tenant isolation, compliance controls, and formal security review.

---

# 46. API Error Contract

All API errors should use a consistent structure.

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The requested clinical document was not found.",
    "request_id": "req_123"
  }
}
```

Useful error codes:

```text
PATIENT_NOT_FOUND
ENCOUNTER_NOT_FOUND
DOCUMENT_NOT_FOUND
ASSET_NOT_FOUND
INVESTIGATION_NOT_FOUND
INVALID_INVESTIGATION_STATE
TOOL_EXECUTION_FAILED
AGENT_EXECUTION_FAILED
VALIDATION_ERROR
INTERNAL_ERROR
```

---

# 47. Investigation API

## Start

```http
POST /api/investigations
```

Request:

```json
{
  "patient_id": "SYN-001",
  "objective": "full_record_investigation"
}
```

Response:

```json
{
  "investigation_id": "INV-001",
  "status": "queued"
}
```

---

## Get state

```http
GET /api/investigations/{investigation_id}
```

Returns:

```text
status
patient
progress
agent statuses
finding counts
timestamps
```

---

## Get events

```http
GET /api/investigations/{investigation_id}/events
```

Used for history/replay.

---

## Stream events

```http
GET /api/investigations/{investigation_id}/stream
```

SSE endpoint.

---

## Get findings

```http
GET /api/investigations/{investigation_id}/findings
```

---

## Get report

```http
GET /api/investigations/{investigation_id}/report
```

---

# 48. Background Execution

Do not run the entire investigation inside the HTTP request.

Bad:

```text
POST /investigations
       ↓
wait 3 minutes
       ↓
return response
```

Instead:

```text
POST /investigations
       ↓
create investigation
       ↓
return ID immediately
       ↓
background worker
       ↓
investigation execution
```

For the hackathon, an asyncio-based worker can be sufficient.

If execution becomes more demanding, introduce a proper queue such as Redis + a worker system.

Do not add infrastructure prematurely.

---

# 49. Logging

Use structured JSON logs.

Every investigation operation should include:

```text
request_id
investigation_id
agent_run_id
tool_execution_id
event_type
duration
status
```

Example:

```json
{
  "event": "tool.completed",
  "investigation_id": "INV-001",
  "agent": "timeline",
  "tool": "get_clinical_notes",
  "records": 8,
  "duration_ms": 412
}
```

Never log hidden ground truth.

---

# 50. Observability

For the hackathon, implement:

- Structured logs.
- Investigation event history.
- Tool execution timing.
- Agent execution timing.
- Error tracking.
- Investigation completion metrics.

Later:

```text
OpenTelemetry
Prometheus
Grafana
centralized logging
```

can be introduced.

---

# 51. Backend Testing Strategy

## Unit tests

Test:

- Timeline normalization.
- Lab comparisons.
- Medication interval calculations.
- Evidence verification.
- Source resolution.
- Tool permission checks.
- Pydantic schemas.

## Tool tests

For every tool:

```text
valid input
invalid input
missing record
multiple records
empty result
```

## Agent tests

Provide deterministic fixtures and validate structured outputs.

## Integration tests

Test:

```text
API
 ↓
service
 ↓
database
 ↓
tool
 ↓
agent
```

## Full investigation test

The most important test:

```text
CASE-001
    ↓
start investigation
    ↓
retrieve records
    ↓
timeline analysis
    ↓
contradiction investigation
    ↓
verification
    ↓
synthesis
    ↓
expected finding
```

The final result should be compared against the hidden evaluation fixture.

---

# 52. Backend Development Phases

## Phase 1 — Clinical data foundation

Build:

- SQLite.
- SQLAlchemy models.
- Alembic.
- Case loader.
- CASE-001 through CASE-010 validation.
- Clinical APIs.

**Deliverable:** A functioning simulated hospital backend.

---

## Phase 2 — Asset and document system

Build:

- Document metadata.
- PDF storage.
- Image storage.
- Document retrieval.
- Imaging endpoints.
- Provenance metadata.

**Deliverable:** Every multimodal artifact is accessible through the backend.

---

## Phase 3 — Tool layer

Build:

- Tool registry.
- Retrieval tools.
- Tool schemas.
- Tool permissions.
- Tool execution logs.

**Deliverable:** A test agent can genuinely retrieve patient records through tools.

---

## Phase 4 — Investigation engine

Build:

- Investigation state.
- Agent runtime.
- Retrieval Agent.
- Timeline Agent.
- Laboratory Agent.
- Medication Agent.
- Contradiction Agent.
- Synthesis Agent.

**Deliverable:** CASE-001 can be investigated end-to-end.

---

## Phase 5 — Evidence engine

Build:

- Finding storage.
- Source references.
- Verification engine.
- Evidence graph.
- Ground-truth evaluator.

**Deliverable:** Every major finding can be independently verified.

---

## Phase 6 — Real-time integration

Build:

- Investigation events.
- Event persistence.
- SSE.
- Frontend integration.

**Deliverable:** The UI shows the actual investigation happening in real time.

---

## Phase 7 — Reliability

Test:

- repeated investigations
- model failures
- tool failures
- missing documents
- ambiguous timestamps
- partial records
- invalid agent outputs
- reconnect behavior
- investigation recovery

---

# 53. Backend Definition of Done

The backend is ready for the hackathon when:

### Hospital system

- CASE-001 through CASE-010 are seeded.
- Patients have linked encounters.
- Encounters have linked documents.
- Documents have linked observations/medications/imaging where appropriate.
- PDFs and images resolve correctly.
- All source IDs are stable.

### Agent system

- Agents have explicit responsibilities.
- Agents use real executable tools.
- Tools access the hospital service rather than the database directly.
- Agents cannot access ground truth.
- Agent outputs are schema validated.
- Tool calls are logged.

### Investigation system

- Investigations are persistent.
- Agents can run independently and in parallel.
- Contradiction investigations can trigger targeted retrieval.
- Findings are verified deterministically.
- Final reports contain evidence references.
- Failed agents do not destroy the entire investigation.

### Frontend integration

- Investigation state can be streamed.
- Tool events appear in the frontend.
- Findings link to source documents.
- The final report loads from backend state.

### Evaluation

- CASE-001 has an expected result.
- The investigation can be run repeatedly.
- Findings can be compared against ground truth.
- Unsupported claims can be detected.
- Source citation accuracy can be measured.

---

# 54. The Critical Architectural Boundary

The entire backend should preserve this separation:

```text
                 ┌─────────────────────┐
                 │  SYNTHETIC HOSPITAL │
                 │                     │
                 │ Patients            │
                 │ Encounters          │
                 │ Labs                │
                 │ Medications         │
                 │ Notes               │
                 │ Reports             │
                 │ Imaging             │
                 └──────────┬──────────┘
                            │
                       Tool Layer
                            │
                            ▼
                 ┌─────────────────────┐
                 │  INVESTIGATION      │
                 │      ENGINE         │
                 │                     │
                 │ Retrieval Agent     │
                 │ Timeline Agent      │
                 │ Lab Agent           │
                 │ Medication Agent    │
                 │ Contradiction Agent │
                 │ Synthesis Agent     │
                 └──────────┬──────────┘
                            │
                      Evidence Engine
                            │
                            ▼
                 ┌─────────────────────┐
                 │   INVESTIGATION     │
                 │       REPORT        │
                 │                     │
                 │ Findings            │
                 │ Sources             │
                 │ Contradictions      │
                 │ Uncertainty         │
                 │ Limitations         │
                 └─────────────────────┘


                 ┌─────────────────────┐
                 │     GROUND TRUTH    │
                 │     (ISOLATED)      │
                 │                     │
                 │ Expected findings   │
                 │ Hidden contradictions│
                 │ Evaluation rules    │
                 └─────────────────────┘
```

That last box is extremely important.

**CASETRACE should never be a system where the LLM is handed the mystery and asked to tell a story about it.**

It should be:

> **A simulated clinical information environment + real retrieval tools + specialized investigators + evidence verification.**

That architecture is what makes the hackathon demo credible and, more importantly, gives you a foundation that can later connect the same investigation engine to authorized real-world clinical systems.
