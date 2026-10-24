# AGENTS.md — CASETRACE

## Finalized implementation stack

Use Next.js App Router + TypeScript + pnpm, FastAPI + Python 3.12+ + uv,
and SQLite + aiosqlite + SQLAlchemy 2.x asyncio + Alembic for the MVP.
Preserve Tailwind CSS and shadcn/ui. Read [development stack and SQLite
operations](docs/development-stack.md) before setup, persistence, migration,
or concurrency work. It defines toolchain baselines, planned commands,
absolute database path resolution, WAL, per-connection foreign keys and busy
timeout, short sessions, guarded state updates, test isolation and recovery.
Agents retain the existing tool/service boundary and never hold transactions
while waiting for inference or external operations. Runtime state belongs in
`data/runtime/casetrace.db`; never commit it or its sidecars. Local development
is preferred; optional Docker needs only API/web with persistent writable
runtime storage, one API process, and no separate database service.

Development skills are installed in `.skill/<name>/SKILL.md`. Application manifests,
lockfiles and foundation commands exist; see [local development](docs/local-development.md).
The original pre-domain contract gate is historical: [Phase 2 contract decisions](docs/CONTRACT_DECISIONS.md)
and [Phase 3 decisions](docs/phase-3-decisions.md) record the implemented resolutions.
Remaining gaps and compatibility constraints are tracked in the
[Refactor 01 audit](docs/refactoring/01-current-state-audit.md). Documentation-only
alignment must not add product features.

## 1. Mission

You are an AI coding agent working on **CASETRACE**.

CASETRACE is an AI clinical investigation system that reconstructs medical mysteries from longitudinal patient records.

The core idea is:

> **CASETRACE does not simply summarize a patient's records. It investigates them, connects evidence across time, identifies contradictions, verifies findings, and produces an evidence-backed investigation report.**

The current hackathon hero case is:

> **A timeline contradiction that becomes visible only when multiple clinical records are connected.**

The system must feel like a realistic clinical information environment combined with a specialized AI investigation engine.

---

# 2. Read Before Coding

Before making significant changes, read these documents:

```text
docs/backend-architecture.md
docs/frontend-backend-contract.md
docs/case-schema.md
docs/hospital-api.md
docs/agent-tools.md
```

If one of these files does not yet exist, do not invent its contract silently.

Create or update the relevant documentation first when necessary.

The architecture documents are authoritative.

If code and documentation disagree:

1. Identify the disagreement.
2. Determine whether the change is intentional.
3. Update the documentation.
4. Then update the implementation.

Do not silently create a second architecture.

---

# 3. Core Architecture

CASETRACE has four major layers:

```text
                    CASETRACE
                        │
                        ▼
              ┌──────────────────┐
              │ Simulated        │
              │ Hospital System  │
              └────────┬─────────┘
                       │
                 Clinical Tools
                       │
                       ▼
              ┌──────────────────┐
              │ Investigation    │
              │ Engine            │
              └────────┬─────────┘
                       │
              Specialized Agents
                       │
                       ▼
              ┌──────────────────┐
              │ Evidence Engine  │
              └────────┬─────────┘
                       │
                       ▼
              Investigation Report
```

The most important architectural boundary is:

```text
Hospital Data
     ↓
Clinical Service
     ↓
Tool Layer
     ↓
Agents
```

Agents do **not** directly access:

```text
SQLite
SQLAlchemy
filesystem
raw case JSON
ground truth
```

Agents interact with clinical data through defined tools.

---

# 4. Non-Negotiable Rules

These rules must not be violated without explicit architectural approval.

## Rule 1 — Agents never access the database directly

Never write agent code like:

```python
await db.execute(...)
```

or:

```python
session.query(...)
```

inside an agent.

Correct:

```text
Agent
  ↓
Tool
  ↓
Clinical Service
  ↓
Repository
  ↓
Database
```

---

## Rule 2 — Ground truth is isolated

Agents must never have access to:

```text
ground_truth
expected_answer
evaluation_answer
hidden_contradiction
```

Do not expose ground truth through:

```text
API
tool
agent context
prompt
frontend
database query
```

Ground truth exists only for evaluation.

---

## Rule 3 — LLMs propose; deterministic code verifies

Never trust an LLM for authoritative:

```text
dates
timestamps
lab values
source IDs
document IDs
medication dates
evidence existence
```

The model can propose:

```text
"This appears contradictory."
```

The backend must verify:

```text
Does the referenced record exist?
Do the timestamps actually conflict?
Does the laboratory value actually match?
Does the document actually contain the referenced information?
```

---

## Rule 4 — Never invent clinical records

If a record does not exist, the system must not fabricate it.

Never invent:

```text
patient
encounter
lab
medication
diagnosis
document
image
timestamp
clinical measurement
source reference
```

If evidence is missing, represent it as missing.

---

## Rule 5 — Every important finding must have evidence

A finding should be traceable:

```text
Finding
   ↓
Evidence
   ↓
Original clinical record
```

Unsupported conclusions are unacceptable.

---

## Rule 6 — Do not expose chain-of-thought

The system may expose:

```text
agent activity
tool calls
records retrieved
findings
verification results
evidence
```

It must not expose:

```text
private chain-of-thought
hidden reasoning
internal prompts
raw model deliberation
```

---

## Rule 7 — Preserve provenance

Whenever data moves through the system, preserve:

```text
source ID
source type
record ID
timestamps
document references
```

Do not strip provenance simply because an agent receives a simplified representation.

---

## Rule 8 — Preserve timestamp semantics

Never collapse:

```text
occurred_at
documented_at
reported_at
ordered_at
specimen_collected_at
```

into one generic timestamp.

CASETRACE's hero contradiction depends on accurate chronology.

---

## Rule 9 — Do not over-engineer

This is a hackathon system.

Prefer:

```text
simple
explicit
testable
reliable
```

over:

```text
distributed
abstract
generic
overly autonomous
```

Do not introduce:

```text
Kafka
Kubernetes
microservices
graph databases
complex workflow platforms
Redis
```

unless there is a demonstrated need.

For the first version, a FastAPI application, SQLite, asyncio workers, and SSE are sufficient.

---

# 5. Product Philosophy

CASETRACE should not feel like:

```text
User → chatbot → answer
```

It should feel like:

```text
Patient record
      ↓
Record discovery
      ↓
Timeline reconstruction
      ↓
Specialist investigations
      ↓
Candidate finding
      ↓
Targeted evidence retrieval
      ↓
Verification
      ↓
Evidence-backed conclusion
```

The frontend should make this process visible.

The backend should make this process real.

Do not fake the investigation with frontend animations.

If the UI shows:

```text
Retrieving laboratory records...
```

the backend should actually have executed a laboratory retrieval operation.

---

# 6. Repository Structure

Expected structure:

```text
CASETRACE/
│
├── AGENTS.md
├── README.md
├── docker-compose.yml
│
├── docs/
│   ├── backend-architecture.md
│   ├── frontend-backend-contract.md
│   ├── case-schema.md
│   ├── hospital-api.md
│   ├── agent-tools.md
│   └── demo.md
│
├── apps/
│   │
│   ├── api/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── alembic/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       ├── hooks/
│       ├── types/
│       ├── public/
│       ├── package.json
│       └── Dockerfile
│
├── data/
│   ├── cases/
│   ├── assets/
│   └── seed/
│
├── scripts/
│   ├── validate_case.py
│   ├── seed_case.py
│   └── seed_all_cases.py
│
└── .env.example
```

Do not reorganize the repository without a strong reason.

---

# 7. Backend Architecture

Backend:

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2
SQLite
Alembic
asyncio
SSE
pytest
```

Backend layers:

```text
API
 ↓
Application Services
 ↓
Investigation / Hospital Services
 ↓
Tools / Agents
 ↓
Repositories
 ↓
SQLite
```

Keep boundaries explicit.

---

# 8. Backend Directory Responsibilities

```text
app/api/
```

HTTP endpoints only.

```text
app/models/
```

SQLAlchemy database models.

```text
app/schemas/
```

Pydantic request/response models.

```text
app/hospital/
```

Clinical information system abstraction and implementation.

```text
app/tools/
```

Agent-accessible clinical tools.

```text
app/agents/
```

Specialized investigation agents.

```text
app/orchestration/
```

Investigation workflow and state management.

```text
app/evidence/
```

Evidence collection and deterministic verification.

```text
app/llm/
```

Provider abstraction and prompts.

```text
app/evaluation/
```

Ground truth and evaluation.

```text
app/workers/
```

Background investigation execution.

---

# 9. Frontend Architecture

Frontend:

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
```

The frontend should be organized around product concepts rather than backend implementation details.

Recommended:

```text
apps/web/
├── app/
├── components/
│   ├── patients/
│   ├── encounters/
│   ├── timeline/
│   ├── documents/
│   ├── labs/
│   ├── medications/
│   ├── imaging/
│   ├── investigations/
│   ├── findings/
│   └── evidence/
│
├── lib/
│   ├── api/
│   ├── sse/
│   └── utils/
│
├── hooks/
└── types/
```

---

# 10. Frontend API Rule

Never call the backend directly from arbitrary components.

Bad:

```typescript
fetch("http://localhost:8000/api/patients/SYN-001")
```

Use:

```typescript
patientsApi.getPatient(patientId)
```

or the appropriate centralized API function.

All API communication should be centralized.

---

# 11. API Contract

The authoritative frontend/backend contract is:

```text
docs/frontend-backend-contract.md
```

The frontend must follow that document.

Important endpoints:

```text
GET  /api/patients
GET  /api/patients/{id}

GET  /api/patients/{id}/encounters
GET  /api/patients/{id}/observations
GET  /api/patients/{id}/medications
GET  /api/patients/{id}/documents
GET  /api/patients/{id}/imaging

POST /api/investigations

GET  /api/investigations/{id}
GET  /api/investigations/{id}/events
GET  /api/investigations/{id}/findings
GET  /api/investigations/{id}/report

GET  /api/investigations/{id}/stream
```

Do not invent alternative endpoints merely because they are convenient for a component.

---

# 12. Investigation Workflow

The initial investigation workflow is intentionally controlled.

```text
                    Investigation
                          │
                          ▼
                   Retrieval Agent
                          │
                          ▼
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         Timeline       Labs       Medication
           Agent        Agent         Agent
             │            │            │
             └────────────┼────────────┘
                          ▼
                 Candidate Findings
                          │
                          ▼
              Contradiction Investigator
                          │
                          ▼
                    Verification
                          │
                          ▼
                  Synthesis Agent
                          │
                          ▼
                  Final Investigation
```

Do not turn this into an unrestricted swarm.

---

# 13. Agent Responsibilities

## Retrieval Agent

Purpose:

> Discover what clinical information exists.

It should identify:

```text
patient
encounters
documents
labs
medications
imaging
```

It should not solve the mystery.

---

## Timeline Agent

Purpose:

> Reconstruct chronology and identify potential temporal inconsistencies.

It must preserve:

```text
occurred_at
documented_at
reported_at
```

It produces candidate discrepancies.

It does not independently declare a contradiction verified.

---

## Laboratory Agent

Purpose:

> Analyze laboratory results over time.

It may identify:

```text
trends
changes
abnormal values
missing measurements
temporal relationships
```

Numerical claims must be verified against actual observations.

---

## Medication Agent

Purpose:

> Reconstruct medication history and identify clinically relevant changes.

Distinguish:

```text
ordered
prescribed
documented
administered
reported as taking
```

Never infer causality without evidence.

---

## Contradiction Investigator

This is the hero investigator for CASE-001.

It takes candidate discrepancies and performs targeted retrieval.

Example:

```text
Candidate contradiction
        ↓
Retrieve document
        ↓
Retrieve laboratory result
        ↓
Retrieve encounter
        ↓
Compare timestamps
        ↓
Check documentation delay
        ↓
Verify
```

Possible classifications:

```text
VERIFIED_CONTRADICTION
DOCUMENTATION_DELAY
AMBIGUOUS
FALSE_POSITIVE
INSUFFICIENT_EVIDENCE
```

---

## Synthesis Agent

Purpose:

> Produce the final investigation report from verified evidence.

It should consume:

```text
verified findings
rejected findings
unresolved findings
timeline
evidence graph
limitations
```

It should not invent additional evidence.

---

# 14. Agent Tool Usage

Agents must use tools.

Example:

```text
Timeline Agent
     ↓
get_encounters()
     ↓
get_clinical_notes()
     ↓
get_lab_results()
```

Do not give agents the complete patient dataset simply to make implementation easier.

That defeats the architecture.

---

# 15. Tool Contract

Every tool must define:

```text
name
description
input schema
permission scope
handler
output schema
audit logging
```

Example:

```python
Tool(
    name="get_lab_results",
    description="Retrieve laboratory observations for a patient.",
    ...
)
```

Tool results must include provenance.

Example:

```json
{
  "status": "success",
  "records": [],
  "source_refs": [],
  "retrieved_at": "..."
}
```

---

# 16. Tool Permissions

Use explicit tool scopes.

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

Laboratory Agent
    observation.read
    document.read

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

Do not give every agent every tool.

---

# 17. Database Rules

Use SQLite.

Use SQLAlchemy 2.

Use Alembic for migrations.

Never modify production database structure manually.

When changing a model:

```text
Modify model
    ↓
Create migration
    ↓
Review migration
    ↓
Run migration
    ↓
Run tests
```

Never silently modify existing migrations that may already have been applied.

---

# 18. Clinical Data Model

The clinical domain includes:

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

The investigation domain includes:

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

Do not merge these domains simply because the tables are convenient to access together.

---

# 19. Clinical Data Immutability

Agents investigate clinical records.

They do not modify them.

The following should be treated as read-only during investigation:

```text
patient
encounter
observation
medication
document
diagnostic report
imaging
referral
```

If an investigation needs derived information, store it in the investigation domain.

---

# 20. Evidence Rules

Every important finding should have:

```text
claim
status
source references
verification state
creator/agent
timestamps
```

Example:

```text
Finding
   │
   ├── supports → DOC-021
   ├── contradicts → LAB-009
   └── contextualizes → ENC-002
```

Supported relationships:

```text
supports
contradicts
contextualizes
derived_from
```

---

# 21. Verification Rules

The verification engine must be deterministic whenever possible.

Verify:

```text
source existence
date
value
document reference
relationship
evidence completeness
```

Example:

```python
if claimed_date != actual_date:
    reject_finding()
```

Do not ask another LLM to decide whether a database timestamp equals a database timestamp.

---

# 22. LLM Provider Abstraction

Agents must never directly import:

```python
google.generativeai
anthropic
openai
```

inside agent files.

Use:

```text
LLMProvider
```

with implementations:

```text
GeminiProvider
OpenAIProvider
AnthropicProvider
LocalProvider
```

This allows the model provider to change without rewriting the investigation engine.

---

# 23. Structured LLM Outputs

Use Pydantic schemas.

Bad:

```python
response = await llm.generate(...)
text = response.text
```

and then manually parse arbitrary prose.

Prefer:

```python
result = await llm.generate(
    ...,
    response_schema=TimelineDiscrepancy
)
```

All important agent outputs must be structured.

---

# 24. Prompt Rules

Prompts belong in:

```text
app/llm/prompts/
```

not scattered through agent implementations.

Each prompt should define:

```text
ROLE
OBJECTIVE
AVAILABLE INFORMATION
AVAILABLE TOOLS
CONSTRAINTS
OUTPUT SCHEMA
```

Agents should explicitly be told:

```text
Do not invent records.
Do not invent dates.
Do not invent values.
Do not invent source IDs.
Cite evidence.
Express uncertainty.
Request additional evidence when necessary.
```

---

# 25. Case Data

Synthetic cases live under:

```text
data/cases/
```

Expected:

```text
CASE-001
CASE-002
...
CASE-010
```

Each case should have:

```text
patient
encounters
clinical events
observations
medications
documents
imaging
assets
ground truth
```

The exact schema is defined in:

```text
docs/case-schema.md
```

---

# 26. Case Generation Rules

Synthetic cases must be:

```text
internally coherent
clinically plausible
temporally structured
multimodal
traceable
deterministically verifiable
```

Cases should contain realistic combinations of:

```text
clinical notes
laboratory reports
prescriptions
encounter records
referrals
radiology reports
synthetic imaging
scanned-style documents
medication history
```

Do not add random noise simply to make the case look complex.

Every artifact should have a purpose.

---

# 27. CASE-001 Priority

CASE-001 is the first complete end-to-end case.

The hero mystery is:

> **Timeline contradiction**

The contradiction should only become obvious after connecting multiple records.

The coding agent should prioritize making:

```text
CASE-001
    ↓
Hospital system
    ↓
Tools
    ↓
Agents
    ↓
Verification
    ↓
Report
```

work completely before optimizing CASE-002 through CASE-010.

---

# 28. Synthetic Asset Rules

PDFs and images belong in:

```text
data/assets/
```

Database stores metadata and relationships.

Do not store large binary files directly inside SQLite unless explicitly required.

Use an abstraction:

```python
AssetStorage
```

This allows future migration to S3-compatible object storage.

---

# 29. API Rules

All API responses must use Pydantic schemas.

Do not return SQLAlchemy models directly.

Bad:

```python
return patient
```

Prefer:

```python
return PatientResponse.model_validate(patient)
```

API errors must use the shared error contract.

---

# 30. API URLs

Backend:

```text
/api/patients
/api/encounters
/api/documents
/api/investigations
```

Frontend must use:

```env
NEXT_PUBLIC_API_URL
```

Never hardcode production URLs.

---

# 31. SSE Rules

Investigation activity is streamed through:

```text
GET /api/investigations/{id}/stream
```

Events include:

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

The frontend must be able to reconnect.

SSE is an activity stream, not the source of truth.

---

# 32. State vs Activity

Important rule:

> **REST represents state. SSE represents activity.**

Use REST to retrieve:

```text
patient state
investigation state
findings
report
clinical records
```

Use SSE to show:

```text
what the investigation is doing right now
```

Never make the application depend on SSE as the only copy of investigation state.

---

# 33. Frontend State Rules

The frontend should maintain:

```text
investigation
agents
events
findings
active tools
report
connection status
error
```

When SSE disconnects:

```text
Reconnect
    ↓
GET investigation state
    ↓
Reconcile
    ↓
Resume SSE
```

Do not reset the investigation UI to an empty state.

---

# 34. Frontend Component Rules

Components should be:

```text
small
composable
domain-focused
```

Prefer:

```text
InvestigationTimeline
AgentActivityPanel
FindingCard
EvidencePanel
ClinicalDocumentViewer
LabResultCard
MedicationTimeline
```

over one massive:

```text
InvestigationPage.tsx
```

Do not create a giant component containing all investigation logic.

---

# 35. Frontend Design Principle

CASETRACE is not a chatbot UI.

Avoid making the main investigation interface:

```text
message bubble
message bubble
message bubble
```

Instead emphasize:

```text
timeline
agents
evidence
findings
relationships
verification
report
```

The interface should communicate:

> "The system investigated this case."

not:

> "The AI chatted about this patient."

---

# 36. Demo Experience

The hero demo should approximately feel like:

```text
Patient selected
       ↓
Investigation started
       ↓
Records discovered
       ↓
Timeline reconstructed
       ↓
Specialists investigate in parallel
       ↓
Potential contradiction appears
       ↓
Contradiction investigator retrieves evidence
       ↓
Evidence verified
       ↓
Finding becomes VERIFIED
       ↓
Final investigation report
```

Every major visual event should correspond to real backend activity.

---

# 37. Do Not Fake Backend Activity

Never implement:

```typescript
setTimeout(() => showAgentRunning(), 2000)
```

just to create the illusion of investigation.

If a visual event is important enough to show:

```text
Agent searching records
```

it should originate from a backend event.

Animations may smooth the presentation, but they must not fabricate system behavior.

---

# 38. Error Handling

Never swallow errors.

Bad:

```python
try:
    ...
except Exception:
    pass
```

or:

```typescript
catch {
  return null;
}
```

unless the error is explicitly handled and intentionally non-fatal.

Errors should be:

```text
logged
classified
returned
or recovered from
```

---

# 39. Partial Failure

One agent failing should not automatically destroy the entire investigation.

Example:

```text
Retrieval       ✓
Timeline        ✓
Laboratory      ✓
Medication      ✗
Contradiction   ✓
Synthesis       ✓
```

The final investigation may become:

```text
completed_with_limitations
```

with:

```text
Medication Agent failed during investigation.
Medication-related conclusions may be incomplete.
```

---

# 40. Guardrails

Investigations must have limits.

Examples:

```text
max investigation duration
max agent iterations
max tool calls per agent
max LLM tokens
max concurrent agents
```

Do not allow an agent to loop indefinitely.

---

# 41. Logging

Use structured logging.

Important fields:

```text
request_id
investigation_id
agent_run_id
tool_execution_id
event_type
duration
status
```

Do not log:

```text
API keys
secrets
ground truth
unnecessary sensitive clinical content
```

---

# 42. Testing Requirements

Every significant backend feature requires tests.

Minimum categories:

```text
unit
integration
tool
agent
investigation
```

Examples:

```text
Timeline timestamp normalization
Evidence verification
Tool permission enforcement
Finding source validation
Investigation lifecycle
SSE event generation
CASE-001 end-to-end investigation
```

---

# 43. CASE-001 End-to-End Test

This is one of the most important tests.

The system should be able to execute:

```text
CASE-001
   ↓
start investigation
   ↓
retrieve records
   ↓
timeline analysis
   ↓
laboratory analysis
   ↓
medication analysis
   ↓
candidate contradiction
   ↓
targeted contradiction investigation
   ↓
deterministic verification
   ↓
synthesis
   ↓
final report
```

The expected finding should be checked against the isolated evaluation fixture.

---

# 44. Frontend Testing

Test:

```text
patient loading
clinical record rendering
investigation creation
investigation state
SSE connection
SSE reconnection
event deduplication
finding rendering
evidence navigation
report rendering
API error states
empty states
```

The investigation UI should be testable without requiring a live LLM for every frontend test.

Use fixtures/mocked API responses where appropriate.

---

# 45. Coding Workflow

When implementing a feature:

### Step 1 — Understand

Read the relevant architecture and contract.

### Step 2 — Inspect

Inspect existing code before creating files.

### Step 3 — Plan

Identify:

```text
files to change
interfaces affected
database changes
API changes
tests required
```

### Step 4 — Implement

Make the smallest coherent implementation.

### Step 5 — Test

Run relevant tests.

### Step 6 — Validate

Check:

```text
architecture
API contract
types
errors
edge cases
```

### Step 7 — Report

Tell the user:

```text
what changed
what was tested
what remains
```

Do not claim tests passed if they were not actually run.

---

# 46. Before Editing Existing Code

Always inspect:

```text
file
imports
callers
interfaces
tests
related schemas
```

Do not blindly overwrite files.

Preserve existing working behavior unless the task explicitly requires changing it.

---

# 47. When to Refactor

Refactor when:

```text
duplication is substantial
a boundary is clearly violated
a module has become unmaintainable
a contract cannot be implemented cleanly
```

Do not refactor merely because another structure looks prettier.

Avoid broad unrelated changes.

---

# 48. Dependency Rules

Before adding a dependency:

Ask:

```text
Do we actually need it?
Can the existing stack solve the problem?
Does it significantly increase complexity?
Will it help the hackathon demo?
```

Do not add a dependency for a problem that can be solved with a small amount of existing code.

---

# 49. Environment Rules

Never commit:

```text
.env
.env.local
API keys
database passwords
private credentials
```

Use:

```text
.env.example
```

for required configuration.

---

# 50. Docker Rules

The development environment should support:

```text
SQLite
FastAPI
Next.js
```

Do not introduce unnecessary services.

Initial architecture:

```text
docker-compose
    │
    ├── api
    └── web
```

Additional services should be justified.

---

# 51. Database Migration Rules

Before changing schema:

```text
1. Modify SQLAlchemy model.
2. Generate migration.
3. Inspect migration manually.
4. Apply migration.
5. Run tests.
```

Do not blindly trust autogenerated migrations.

---

# 52. Data Seeding Rules

Use:

```text
scripts/validate_case.py
scripts/seed_case.py
scripts/seed_all_cases.py
```

A case must pass validation before seeding.

Never manually insert important demo records through ad-hoc SQL.

---

# 53. Clinical Safety Rules

CASETRACE is a hackathon prototype using synthetic data.

It must never imply that it is making real clinical decisions.

The system should distinguish:

```text
record evidence
investigative finding
clinical interpretation
causal conclusion
```

Do not present unsupported medical conclusions as facts.

Prefer:

```text
"The records indicate..."
"The available evidence supports..."
"The timeline suggests..."
"The available records do not establish..."
```

Avoid unsupported:

```text
"This medication caused..."
"The patient definitely had..."
"The doctor made an error..."
```

unless the underlying evidence and evaluation explicitly support such a conclusion.

---

# 54. Synthetic Data Safety

All demo patient information must be synthetic.

Do not introduce real patient information into:

```text
fixtures
tests
screenshots
logs
demo videos
documentation
```

---

# 55. Evidence Language

Use precise language.

Preferred:

```text
Verified contradiction
Potential discrepancy
Documentation delay
Insufficient evidence
Unresolved
```

Avoid dramatic unsupported language such as:

```text
The doctor lied.
The hospital made a fatal mistake.
The patient was misdiagnosed.
```

unless the case is specifically designed and verified to establish such a claim.

---

# 56. Code Quality

Prefer:

```python
async def get_lab_results(
    patient_id: str,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> list[Observation]:
    ...
```

over unnecessarily complex abstractions.

Use:

```text
clear names
small functions
explicit types
Pydantic schemas
dependency injection
```

Avoid:

```text
magic strings
global mutable state
huge functions
deep inheritance hierarchies
unnecessary generic abstractions
```

---

# 57. Type Safety

Backend:

```text
Python type hints
Pydantic validation
```

Frontend:

```text
TypeScript
Zod where appropriate
```

Do not use:

```typescript
any
```

as a shortcut.

If `any` appears to be necessary, first determine whether the API contract is missing a proper type.

---

# 58. Async Rules

The backend is asynchronous.

Do not perform blocking operations directly inside async request handlers.

Be careful with:

```text
filesystem
LLM calls
HTTP requests
database operations
```

Use appropriate async APIs.

---

# 59. API Client Rules

Frontend API calls must have:

```text
typed request
typed response
error handling
timeout/recovery strategy where appropriate
```

Do not duplicate API request logic across components.

---

# 60. SSE Client Rules

Implement a reusable SSE layer.

Recommended:

```text
apps/web/lib/sse/
    investigation-stream.ts
```

It should handle:

```text
connection
events
reconnection
cleanup
deduplication
connection state
```

Components should consume events rather than implement raw SSE logic themselves.

---

# 61. Event Architecture

Events should be generated by the backend investigation engine.

Do not let the frontend infer:

```text
agent started
tool completed
finding verified
```

from unrelated REST responses.

The event system is the authoritative source of investigation activity.

---

# 62. Agent Event Example

When an agent executes:

```text
get_lab_results
```

the backend should emit:

```text
tool.started
```

then execute the tool.

After completion:

```text
tool.completed
```

If a finding is produced:

```text
finding.proposed
```

If verification succeeds:

```text
finding.verified
```

The frontend should reflect those events.

---

# 63. Do Not Leak Implementation Details

The frontend should not display:

```text
SQLAlchemy
SQLite query
Python stack trace
internal class name
LLM provider internals
```

Translate backend activity into domain language.

Bad:

```text
SQL query executed
```

Good:

```text
Retrieved 24 laboratory records
```

Bad:

```text
ContradictionAgent.verify_candidate()
```

Good:

```text
Verifying timeline discrepancy
```

---

# 64. Demo Performance

The hackathon demo should prioritize:

```text
fast startup
predictable investigation
clear activity
credible evidence
stable UI
```

Do not optimize for theoretical scale before demo reliability.

If an expensive operation can be cached safely without compromising the demonstration of real investigation behavior, caching may be used.

Do not fake results.

---

# 65. Determinism

The same CASE-001 should produce reasonably consistent investigative behavior.

Reduce unnecessary nondeterminism through:

```text
structured outputs
controlled prompts
deterministic verification
bounded agent workflows
stable synthetic data
```

Do not depend on a model "remembering" the case.

---

# 66. Agent Context

An agent context may contain:

```text
investigation_id
patient_id
objective
available evidence
previous findings
workflow state
tool permissions
```

It must not contain:

```text
ground truth
evaluation answer
hidden case solution
```

---

# 67. Agent Output

Agent outputs should be structured.

Example:

```python
class AgentResult(BaseModel):
    status: Literal[
        "success",
        "partial",
        "failed"
    ]

    findings: list[FindingProposal]

    source_refs: list[SourceRef]

    notes: list[str]
```

Agents should not return arbitrary strings as their primary output.

---

# 68. Finding Lifecycle

A finding follows:

```text
proposed
    ↓
verification
    ↓
verified
```

or:

```text
proposed
    ↓
verification
    ↓
rejected
```

or:

```text
proposed
    ↓
verification
    ↓
unresolved
```

The frontend should represent this lifecycle clearly.

---

# 69. Investigation Completion

An investigation is complete when:

```text
required agents finished
or
required evidence was exhausted
or
investigation reached a controlled terminal state
```

Never mark an investigation completed simply because an LLM returned a response.

---

# 70. Final Report Rules

The final report must include:

```text
summary
timeline
verified findings
rejected findings where relevant
unresolved questions
supporting evidence
limitations
source references
```

Every major claim should be traceable to evidence.

---

# 71. What the Coding Agent Should NOT Do

Do not:

```text
rewrite the entire project without need
replace architecture without discussion
introduce unnecessary infrastructure
give agents direct database access
expose ground truth
fake tool calls
fake investigation events
invent clinical data
invent API contracts
hardcode localhost URLs
store secrets in source
ignore failing tests
hide errors
return raw SQLAlchemy objects
build giant components
create unrestricted agent swarms
```

---

# 72. When Requirements Are Ambiguous

Do not immediately invent a large solution.

First determine:

```text
What is the smallest interpretation that satisfies the requirement?
```

Prefer the existing architecture.

If a decision materially affects architecture, stop and explain the decision before making a broad change.

---

# 73. Change Scope

When asked:

```text
"Implement X"
```

do not automatically:

```text
rewrite Y
refactor Z
replace dependencies
redesign unrelated components
```

Keep changes focused.

If an adjacent architectural problem blocks implementation, explain it and fix only what is necessary.

---

# 74. Documentation Rule

When behavior changes, update the appropriate documentation.

Examples:

```text
API changed
→ frontend-backend-contract.md

Agent behavior changed
→ agent-tools.md / backend architecture

Case schema changed
→ case-schema.md

Demo behavior changed
→ demo.md
```

Documentation is part of the implementation.

---

# 75. Commit-Ready Standard

Before considering a task complete:

```text
[ ] Code compiles
[ ] Types are valid
[ ] Tests pass
[ ] API contract remains valid
[ ] No secrets introduced
[ ] No ground truth exposed
[ ] Agent boundaries preserved
[ ] Evidence provenance preserved
[ ] Errors handled
[ ] Documentation updated if necessary
```

---

# 76. Definition of Done — Backend

Backend is considered functional when:

```text
[ ] SQLite works
[ ] CASE-001 seeds successfully
[ ] CASE-002 through CASE-010 validate
[ ] Clinical APIs work
[ ] Documents resolve
[ ] Imaging resolves
[ ] Tool layer works
[ ] Tool calls are logged
[ ] Agents use tools
[ ] Agents cannot access ground truth
[ ] Investigation state persists
[ ] Agents execute in controlled workflow
[ ] Evidence is stored
[ ] Findings are verified
[ ] SSE works
[ ] Final report is generated
[ ] CASE-001 end-to-end test passes
```

---

# 77. Definition of Done — Frontend

```text
[ ] Patient list works
[ ] Patient workspace works
[ ] Timeline works
[ ] Labs work
[ ] Medications work
[ ] Documents work
[ ] Imaging works
[ ] Investigation can be started
[ ] Investigation state loads
[ ] SSE works
[ ] Agent activity renders
[ ] Tool activity renders
[ ] Findings render
[ ] Evidence navigation works
[ ] Verification state renders
[ ] Final report renders
[ ] SSE reconnection works
[ ] API errors are handled
```

---

# 78. Definition of Done — CASETRACE Demo

The demo is ready when this entire flow works without manual intervention:

```text
                    USER
                      │
                      ▼
               Select CASE-001
                      │
                      ▼
             Open patient record
                      │
                      ▼
             Click "Investigate"
                      │
                      ▼
             Investigation starts
                      │
                      ▼
             Retrieval Agent
                      │
              records discovered
                      │
                      ▼
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Timeline      Labs      Medication
        Agent       Agent         Agent
          │           │           │
          └───────────┼───────────┘
                      ▼
              Candidate finding
                      │
                      ▼
          Contradiction Investigator
                      │
                targeted tools
                      │
                      ▼
                 Verification
                      │
                      ▼
              VERIFIED FINDING
                      │
                      ▼
              Synthesis Agent
                      │
                      ▼
             Investigation Report
                      │
                      ▼
             Evidence-linked result
```

The important part is that this is **real system behavior**, not a scripted animation.

---

# 79. Priority Order

When deciding what to build next, prioritize:

```text
1. CASE-001 correctness
2. Evidence integrity
3. Tool-based retrieval
4. Investigation workflow
5. Verification
6. Frontend/backend contract
7. Real-time activity
8. Clinical record UX
9. Visual polish
10. Scale optimization
```

Do not reverse this order.

A beautiful interface with fake investigation logic is not CASETRACE.

---

# 80. Strategic Principle

Always preserve this architecture:

```text
             SIMULATED HOSPITAL
                     │
                     ▼
             CLINICAL RECORDS
                     │
                     ▼
              RETRIEVAL TOOLS
                     │
                     ▼
            SPECIALIZED AGENTS
                     │
                     ▼
             CANDIDATE FINDINGS
                     │
                     ▼
           TARGETED INVESTIGATION
                     │
                     ▼
              VERIFICATION
                     │
                     ▼
             EVIDENCE GRAPH
                     │
                     ▼
           INVESTIGATION REPORT
```

CASETRACE's competitive advantage in the demo is not:

> "We connected an LLM to medical documents."

It is:

> **"We built an AI investigator that can navigate a clinical information environment, reconstruct a patient's timeline, discover a hidden contradiction, retrieve the underlying evidence, verify it, and explain exactly why the finding is trustworthy."**

Every engineering decision should strengthen that experience.

---

# 81. Final Rule

When in doubt, choose:

```text
Explicit over magical.
Evidence over assertion.
Tools over hidden access.
Verification over model confidence.
Controlled workflows over uncontrolled autonomy.
Real behavior over demo theater.
Simple architecture over premature infrastructure.
```

And always remember:

> **CASETRACE is an investigation engine, not a chatbot.**
