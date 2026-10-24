# CASETRACE — Architecture & Implementation Specification

Finalized MVP stack: Next.js App Router + TypeScript + pnpm; FastAPI + Python + uv; SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Existing Tailwind CSS/shadcn/ui and investigation behavior remain. See [development stack](development-stack.md) for operational requirements and planned commands.
**Version:** 1.0  
**Project:** Healthcare AI Investigation System  
**Target:** Hackathon prototype  
**Primary objective:** Demonstrate credible, evidence-backed reconstruction of a complex medical case from fragmented, multimodal patient records.

---

## 1. Product Definition

CASETRACE is a multi-agent healthcare investigation system that reconstructs patient histories from fragmented clinical records, identifies contradictions and unresolved findings, and produces an auditable evidence-backed case report.

CASETRACE does not simply answer questions about a patient. It retrieves source records, builds a longitudinal timeline, investigates conflicting evidence, verifies its findings, and explains what the available evidence does and does not establish.

### Core demonstration

A synthetic patient's medical history is distributed across multiple encounters, clinical notes, laboratory records, medication records, and radiology documents.

The agents independently retrieve relevant evidence, discover a contradiction in the documented timeline, investigate related findings, and produce a structured report with traceable source references.

**Demo objective:** Wow factor + evidence credibility.

### Product principles

1. Real tool execution, not simulated agent activity.
2. Synthetic data with explicit provenance and deterministic ground truth.
3. Independent evidence gathering followed by cross-verification.
4. Every major claim linked to its supporting source.
5. Explicit uncertainty where records are incomplete or ambiguous.
6. A clear boundary between a temporal association, a clinical hypothesis, and an established causal relationship.

---

## 2. System Architecture

### High-level architecture

```text
                    CASETRACE FRONTEND
                Next.js + TypeScript
                         |
                  FastAPI Backend
                         |
          +--------------+---------------+
          |              |               |
      Hospital API   Investigation API   Audit API
          |              |               |
          |        Agent Orchestrator     |
          |              |               |
          |      +-------+--------+       |
          |      |       |        |       |
          |   Timeline  Trend   Evidence  |
          |    Agent    Agent   Agent     |
          |      |       |        |       |
          |      +-------+--------+       |
          |              |               |
          |       Verification Engine     |
          |              |               |
          +--------+-----+----------------+
                   |
          +--------+---------+
          |                  |
    SQLite         Synthetic Files
    Clinical data      PDFs, images,
    Metadata, events   notes, reports
```

### Architectural components

**A. Synthetic Case Factory**

Generates complete, internally linked patient cases from a canonical ground-truth specification.

**B. Simulated Hospital / EHR**

Stores patient records and exposes API tools through which agents retrieve information.

**C. Investigation Engine**

Coordinates specialist agents, tool calls, evidence collection, hypothesis testing, and verification.

**D. Investigation Console**

Displays agent activity, retrieved records, the reconstructed timeline, contradictions, and the final report.

**E. Evidence and Audit Layer**

Records retrieval operations, source references, timestamps, agent outputs, verification results, and final report provenance.

### Important architectural boundary

The case ground truth is available to the case-generation and evaluation components, but not to the investigating agents. The agents must discover the findings from accessible source records.

---

## 3. Recommended Technology Stack

| Component | Technology |
|---|---|
| Frontend | Next.js, TypeScript |
| UI | Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI |
| Data validation | Pydantic |
| Database | SQLite |
| Document storage | Local filesystem for hackathon; storage adapter for future object storage |
| Agent orchestration | Explicit Python workflow with typed states and controlled transitions |
| LLM integration | Provider-independent model adapter |
| Structured clinical data | FHIR-inspired resource model |
| Timeline visualization | React-based timeline component |
| Evidence graph | React Flow, if useful for the demo |
| Testing | pytest, API integration tests, deterministic evaluation fixtures |
| Development | Docker Compose, environment-based configuration |

### Implementation decision

Start with an explicit Python orchestrator rather than introducing a large, general-purpose agent framework before the workflow is understood.

Each agent should be a separately testable module with a defined input, output, tool permissions, and completion criteria. The orchestrator should own task assignment, parallel execution, retry limits, and workflow state.

An orchestration framework can be introduced later if it materially simplifies persistence, human approval, or recovery.

---

## 4. Synthetic Case Factory

The Case Factory is foundational because the quality of the investigation depends on the quality and internal consistency of the source data.

### Generation pipeline

1. Define the clinical scenario and ground truth.
2. Define the canonical event timeline.
3. Generate structured records for each event.
4. Generate linked clinical notes and reports.
5. Generate synthetic multimodal artifacts where they contribute evidence.
6. Validate all records against the canonical event store.
7. Generate a separate answer key and evidence map.
8. Run automated consistency checks.
9. Publish the case into the simulated hospital.
10. Run the investigation without exposing the answer key.

### CASE-001: Flagship synthetic case

**Patient:** SYN-001 — Daniel M.  
**Age:** 47  
**Case period:** January 8 – July 22, 2026  
**Encounter structure:** Seven visits across the investigation period.

**Primary mystery:** A critical timeline contradiction becomes apparent only when multiple encounters and original source records are connected.

**Related investigative dimensions:**

- Timeline reconstruction and documentation discrepancies.
- The temporal relationship between lisinopril exposure and cough, without assuming causality.
- An unresolved, nonspecific right lower-lung opacity.
- Competing explanations, including GERD or anxiety, that must be assessed against the complete evidence.

These are investigative hypotheses and evidence relationships, not a predetermined clinical diagnosis.

### Case data schema

Every case must have the following logical entities:

- `Case`: scenario metadata, version, and status.
- `Patient`: synthetic identifier and demographic details.
- `Encounter`: visit date, department, author, and encounter status.
- `ClinicalEvent`: event time, documentation time, event type, and source.
- `ClinicalNote`: narrative text, author, encounter reference, and timestamps.
- `Observation`: test identifier, value, unit, reference range, and observation time.
- `MedicationRecord`: medication, dose, route, start/end dates, and record status.
- `DiagnosticReport`: findings, interpretation, author, and report timestamp.
- `ImagingAsset`: modality, synthetic asset URI, metadata, and provenance.
- `Document`: report or attachment metadata and storage reference.
- `GroundTruth`: hidden canonical facts, intended contradictions, and expected findings.
- `EvidenceReference`: source identifiers and exact record locations supporting a claim.

### Multimodal requirements

A single case may contain:

1. Structured laboratory results and longitudinal measurements.
2. Clinical notes and consultation narratives.
3. Medication orders and medication reconciliation records.
4. Radiology reports.
5. Synthetic illustrative radiology images, where useful.
6. Scanned-style documents or generated PDF reports.
7. Encounter summaries and referral documents.

All artifacts must be fictional, clearly labeled as synthetic, and linked to the correct encounter and underlying event.

Do not create arbitrary images simply to claim multimodality. Each artifact must support a specific investigative question. An illustrative image must never be represented as an authentic patient study.

### Ground-truth answer key

The answer key must define:

- The intended chronology and underlying event sequence.
- The exact contradictory records.
- The relevant medication exposure timeline.
- The unresolved imaging finding.
- The competing hypotheses and evidence relevant to each.
- What the evidence supports.
- What the evidence cannot establish.
- The expected source references for each finding.
- The conditions under which the correct result is “uncertain” or “insufficient evidence.”

**Security requirement:** The answer key must not be available through the hospital retrieval API or agent tool permissions.

---

## 5. Simulated Hospital Environment

The hospital application is a functioning record system, not a static collection of screenshots.

### Hospital UI modules

**A. Hospital dashboard**

- Synthetic patient directory.
- Encounter counts and record categories.
- Case selection and case status.
- Search by synthetic patient identifier.

**B. Patient chart**

- Patient overview.
- Encounter history.
- Clinical notes.
- Laboratory results and trends.
- Medication history.
- Diagnostic and imaging reports.
- Linked documents and attachments.

**C. Encounter detail**

- Encounter date and department.
- Clinician note.
- Observations recorded during the encounter.
- Orders, prescriptions, and reports.
- Links to related encounters.

**D. Document viewer**

- Rendered clinical reports.
- Original document metadata.
- Event date versus documentation date.
- Source record identifier.
- Synthetic-data watermark.

**E. Integration and audit panel**

- API requests and responses.
- Retrieval history.
- Tool execution status.
- Source records accessed by agents.

### Hospital API contract

Implement a deliberately small, documented FHIR-inspired API subset.

Example endpoints:

```text
GET /api/patients
GET /api/patients/{patient_id}
GET /api/patients/{patient_id}/encounters
GET /api/encounters/{encounter_id}
GET /api/patients/{patient_id}/observations
GET /api/patients/{patient_id}/medications
GET /api/patients/{patient_id}/diagnostic-reports
GET /api/patients/{patient_id}/documents
GET /api/documents/{document_id}
```

The implementation should use consistent identifiers, timestamps, pagination where needed, and validated response schemas.

Distinguish event time, specimen collection time, report time, and documentation time. These dates are not interchangeable.

The simulator must also support realistic missing records and incomplete follow-up documentation. An absent record means that the system did not find documentation; it does not prove that an event never occurred.

---

## 6. Multi-Agent Investigation Engine

### Agent 1: Record Retrieval Agent

**Mission:** Discover and retrieve the records required to investigate the selected case.

**Tools:**

- `search_patient`
- `get_encounters`
- `get_clinical_notes`
- `get_lab_results`
- `get_medication_history`
- `get_diagnostic_reports`
- `get_document`

**Output:** Retrieved record manifest, source references, unavailable resources, and retrieval status.

**Completion criteria:** Relevant record categories have been searched, retrieval results are recorded, and missing resources are explicitly identified.

### Agent 2: Timeline Reconstruction Agent

**Mission:** Reconstruct the chronological history from distributed records.

**Responsibilities:**

- Normalize timestamps and time zones.
- Distinguish clinical event time from documentation time.
- Order encounters, medications, symptoms, and test results.
- Identify conflicting dates and sequences.
- Preserve ambiguous timestamps rather than inventing precision.

**Output:** Ordered clinical event timeline and candidate chronology discrepancies.

### Agent 3: Clinical Trend Agent

**Mission:** Identify meaningful longitudinal patterns in available observations.

**Responsibilities:**

- Compare serial test results.
- Check units and reference ranges.
- Identify meaningful changes and missing measurements.
- Associate results with encounters.
- Distinguish observed trends from clinical interpretations.

**Output:** Trend summaries with exact source values, dates, and record identifiers.

### Agent 4: Medication Relationship Agent

**Mission:** Investigate medication exposure and its temporal relationship to documented symptoms and findings.

**Responsibilities:**

- Reconstruct medication start, stop, and change records.
- Compare exposure dates with symptom documentation.
- Identify conflicting or incomplete medication histories.
- Assess alternative explanations without asserting unsupported causality.

**Output:** Medication timeline, relevant temporal associations, conflicting evidence, and unresolved questions.

### Agent 5: Contradiction Investigator

**Mission:** Test candidate discrepancies against original source records.

**Responsibilities:**

- Retrieve source records independently.
- Compare event timestamps and documentation timestamps.
- Verify quotations, values, and encounter references.
- Distinguish a true contradiction from a delayed entry, missing record, or ambiguous timestamp.
- Investigate unresolved findings and conflicting explanations.

**Output:** Verified findings, rejected candidates, unresolved discrepancies, and evidence chains.

### Agent 6: Case Synthesis Agent

**Mission:** Produce the final evidence-backed investigation report.

**Responsibilities:**

- Combine verified findings from specialist agents.
- Explain the central chronology contradiction.
- Present supporting and conflicting evidence.
- Separate facts, hypotheses, and unknowns.
- Identify unresolved issues requiring clinical review.

**Output:** A structured investigation report, not an autonomous definitive diagnosis.

### Shared output contract

Every agent finding should conform to a typed schema similar to:

```python
class EvidenceFinding(BaseModel):
    finding_id: str
    claim: str
    category: str
    source_ids: list[str]
    event_dates: list[datetime]
    confidence: float
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    limitations: list[str]
    verification_status: str
```

The production schema should validate evidence references against retrieved records. Confidence scores must not be treated as calibrated probabilities unless separately evaluated.

---

## 7. Orchestration Workflow

### Investigation state machine

```text
CASE_SELECTED
     |
     v
RECORD_DISCOVERY
     |
     v
RECORD_RETRIEVAL
     |
     v
EVIDENCE_NORMALIZATION
     |
     v
PARALLEL_INVESTIGATION
     |
     +---- Timeline analysis
     +---- Lab trend analysis
     +---- Medication analysis
     +---- Unresolved finding analysis
     |
     v
CONTRADICTION_INVESTIGATION
     |
     v
SOURCE VERIFICATION
     |
     +---- Insufficient evidence --> Targeted retrieval
     |                                  |
     |                                  v
     |                         Re-verify findings
     |
     v
CASE SYNTHESIS
     |
     v
FINAL REPORT
```

### Workflow requirements

- Every tool call must execute a real function.
- Tool calls must be logged with arguments, status, duration, and returned record identifiers.
- Agents must receive only the information and tools needed for their assigned task.
- Specialist agents may run in parallel when their inputs are independent.
- Contradiction investigation must be allowed to request targeted additional retrieval.
- Verification must happen before final synthesis.
- Retry limits and execution timeouts must prevent runaway loops.
- The workflow must preserve partial results if one agent fails.
- The UI must reflect actual backend execution states.

### Deterministic verification

The verifier should use ordinary Python logic wherever possible.

It should check:

- Whether each source identifier exists.
- Whether quoted text matches the retrieved document.
- Whether reported dates match the source record.
- Whether numerical values and units match the source.
- Whether the claimed chronology follows the underlying timestamps.
- Whether the final report labels unresolved findings appropriately.

LLMs may propose interpretations, but they should not be the sole authority for verifying dates, values, or source references.

---

## 8. Evidence Graph and Auditability

Represent important relationships as an evidence graph.

**Nodes:** Patients, encounters, events, documents, observations, medications, findings, and hypotheses.

**Edges:** Belongs to encounter, documented in, occurred before, conflicts with, supports, contradicts, and derived from.

Each major final finding should link back to one or more original records.

The audit trail should preserve:

- Tool name and execution identifier.
- Agent identity.
- Input parameters.
- Retrieved source identifiers.
- Execution status and timestamps.
- Verification results.
- Final findings derived from the operation.

Do not expose private model reasoning traces as the evidence trail. Display observable actions, retrieved evidence, concise rationales, and verifiable results instead.

---

## 9. Frontend Application Structure

Suggested frontend routes:

```text
/
  Hospital dashboard

/patients
  Synthetic patient directory

/patients/[patientId]
  Patient chart

/encounters/[encounterId]
  Encounter details

/documents/[documentId]
  Clinical document viewer

/investigations
  Investigation list

/investigations/[investigationId]
  Live investigation console

/investigations/[investigationId]/report
  Final evidence report
```

### Investigation console layout

**Left panel — Patient context**

- Patient identifier and synthetic-data label.
- Encounter list.
- Available record categories.
- Investigation status.

**Center panel — Investigation activity**

- Agent execution timeline.
- Tool calls and retrieval results.
- Current investigative questions.
- Findings awaiting verification.

**Right panel — Evidence and findings**

- Detected contradictions.
- Linked source records.
- Supporting and conflicting evidence.
- Verification status.

**Final report view**

- Executive summary.
- Reconstructed timeline.
- Verified contradictions.
- Medication and test-result relationships.
- Unresolved findings.
- Evidence references.
- Limitations and clinical review notice.

The interface should prioritize clear information hierarchy and source traceability over decorative animations.

---

## 10. Flagship Demo Sequence

Target duration: approximately 3–4 minutes.

### Phase 1 — Establish the mystery

Open the synthetic hospital environment and select SYN-001. Show that the patient's information is distributed across multiple encounters and record types.

### Phase 2 — Launch the investigation

Start CASETRACE. The UI displays actual tool execution as the retrieval agent searches for encounters, clinical notes, observations, medications, and diagnostic reports.

### Phase 3 — Reveal the discovery

The timeline agent identifies a candidate chronology discrepancy. The contradiction investigator retrieves the original records and verifies the conflicting timestamps or documented sequence.

### Phase 4 — Connect the evidence

The specialist agents examine medication timing and the unresolved imaging finding. The system explains which findings are supported, which relationships remain uncertain, and which source records are relevant.

### Phase 5 — Deliver the report

Present the reconstructed timeline, central contradiction, source evidence, competing explanations, and unresolved questions.

**The key wow moment:** CASETRACE discovers and verifies a finding by navigating multiple records, then lets the audience inspect the underlying evidence themselves.

---

## 11. Repository Structure

```text
casetrace/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── hospital/
│   │   │   ├── agents/
│   │   │   ├── orchestration/
│   │   │   ├── verification/
│   │   │   └── audit/
│   │   └── tests/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── features/
│       ├── lib/
│       └── types/
├── data/
│   ├── cases/
│   │   └── CASE-001/
│   │       ├── manifest.json
│   │       ├── records/
│   │       ├── documents/
│   │       └── assets/
│   └── fixtures/
├── scripts/
│   ├── generate_case.py
│   ├── validate_case.py
│   └── seed_hospital.py
├── docs/
│   ├── architecture.md
│   ├── case-schema.md
│   ├── api-contracts.md
│   ├── agent-workflow.md
│   ├── demo-script.md
│   └── security.md
├── docker-compose.yml
├── .env.example
└── README.md
```

The ground-truth answer key should be stored separately from agent-accessible case data and excluded from the hospital API, frontend bundles, and ordinary application logs.

---

## 12. Implementation Milestones

### Milestone 1 — Case specification

- Finalize CASE-001 ground truth.
- Define the complete event timeline.
- Map each intended discovery to its source evidence.
- Define expected agent findings and failure cases.

### Milestone 2 — Hospital simulator

- Implement database models and synthetic fixtures.
- Build the retrieval API.
- Implement the patient chart and document viewer.
- Verify that every source record is accessible through the API.

### Milestone 3 — Tool layer and retrieval agent

- Implement typed retrieval tools.
- Add execution logging and error handling.
- Demonstrate real record retrieval through the UI.

### Milestone 4 — Investigation workflow

- Implement timeline, trend, medication, and contradiction agents.
- Add parallel execution and targeted retrieval.
- Implement deterministic evidence verification.

### Milestone 5 — Evidence interface

- Build the live investigation console.
- Link findings to source documents.
- Display actual execution status and evidence provenance.
- Generate the final structured report.

### Milestone 6 — Evaluation and demo hardening

- Run the complete investigation repeatedly.
- Test missing records, timestamp ambiguities, and conflicting notes.
- Compare outputs with the hidden ground truth.
- Validate all source citations and numerical values.
- Rehearse the 3–4 minute demo.

---

## 13. Acceptance Criteria

The hackathon build is ready when:

1. CASE-001 contains linked synthetic records across the required modalities.
2. The hospital UI displays the same records accessed by the agents.
3. Agents retrieve evidence through executable backend tools.
4. The primary timeline contradiction is discovered without exposing the answer key.
5. The system can retrieve original source records to verify a candidate finding.
6. Every major final claim has valid evidence references.
7. Missing documentation is not misrepresented as proof that an event did not occur.
8. Medication timing is not automatically presented as proof of causality.
9. The final report distinguishes verified facts, hypotheses, and unresolved questions.
10. The complete investigation can be demonstrated reliably in 3–4 minutes.
11. The application clearly identifies the environment and all patient artifacts as synthetic.
12. The demo makes no claims of real hospital integration or clinical validation.

---

## 14. Scope Boundaries

### Included in the hackathon

- One high-quality flagship case.
- Multiple linked synthetic encounters.
- Structured clinical records and selected document/image artifacts.
- A functioning hospital simulator.
- Real agent tools and controlled orchestration.
- Source verification and evidence-linked reporting.
- A polished investigation interface.

### Deferred until after the hackathon

- Production EHR integrations.
- Real patient data.
- Production-grade SMART on FHIR authorization.
- Deployment across multiple hospital systems.
- Broad medical image interpretation.
- Large-scale synthetic case generation.
- Clinical validation and prospective clinical evaluation.

### Final architectural principle

**The case is the test, the hospital is the environment, the agents are the investigators, and the evidence trail is the proof.**

CASETRACE should be designed so that replacing the synthetic hospital with an authorized real-world connector does not require rebuilding the investigation engine from scratch.
