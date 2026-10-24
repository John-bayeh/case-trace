---
name: investigation
description: 'Implement the evidence-first investigation engine for synthetic hospital histories. This skill coordinates planning, evidence collection, timeline reconstruction, contradiction detection, hypothesis assessment, and an auditable final report. CASETRACE is clinical decision support for a simulated hackathon environment, not an autonomous diagnostician. Use for: Use for work on investigation orchestration, agent workflows, event streams, run persistence, and investigation API endpoints. Read the specialized skill before implementing each stage.'
---

# CASETRACE Investigation — Orchestration Skill

## Purpose
Implement the evidence-first investigation engine for synthetic hospital histories. This skill coordinates planning, evidence collection, timeline reconstruction, contradiction detection, hypothesis assessment, and an auditable final report. CASETRACE is **clinical decision support for a simulated hackathon environment**, not an autonomous diagnostician.

## When to use
Use for work on investigation orchestration, agent workflows, event streams, run persistence, and investigation API endpoints. Read the specialized skill before implementing each stage.

## Required project context
Read `AGENTS.md`, `case-schema.md`, `agent-tools.md`, `hospital-api.md`, `frontend-backend-contract.md`, and backend architecture where available. Treat existing contracts as the source of truth; if a field/route differs from examples here, follow the contract and document the mapping. Never silently introduce a competing API.

## Inputs / outputs
- Input: authorized synthetic `patient_id`, optional `case_id`, investigator objective, permitted tool scope, run settings.
- Output: durable `investigation_id`, ordered activity events, evidence registry, normalized timeline, candidate contradictions, assessed hypotheses, and final report.
- Every source-dependent assertion must carry evidence references; unresolved assertions must be labeled accordingly.

## Canonical investigation stages
1. **Plan**: translate objective into concrete, bounded retrieval tasks.
2. **Collect**: call hospital tools for records; persist raw response references and provenance.
3. **Normalize**: construct a timeline with explicit timestamp semantics and uncertainty.
4. **Detect**: find candidate conflicts; don't equate a discrepancy with clinical error.
5. **Assess**: generate competing explanations and test them against evidence.
6. **Verify**: validate source locations, timestamps, and counterevidence.
7. **Report**: publish a restrained finding with linked sources and confidence rationale.

## Agent topology
- Orchestrator: manages run state and tool budgets.
- Retrieval specialist: calls permitted hospital API tools; does not invent records.
- Timeline specialist: normalizes events and temporal relations.
- Contradiction specialist: identifies and classifies conflicts.
- Hypothesis specialist: develops and tests alternative explanations.
- Evidence verifier: independently resolves all cited references before final output.
- Reporter: renders validated findings, uncertainties, and next-review questions.
These may be logical modules within one FastAPI service; do **not** require separate network services for a hackathon MVP.

## Run state machine
`created → planning → collecting → reconstructing → analyzing → verifying → reporting → completed`; terminal alternatives `failed`, `cancelled`, `insufficient_evidence`. State transitions must be explicit, persisted, and surfaced to frontend. Retries must not duplicate evidence or overwrite previous successful event history. A partial run may show working findings but must not masquerade as verified.

## Core invariants
- Read-only hospital source records during investigation.
- `patient_id` scoping enforced at every tool and repository layer.
- Stable IDs for run, tool call, record, document, event, span/region, evidence, finding.
- Patient data never mixed across cases or tenants; synthetic demo artifacts visibly labeled synthetic.
- All timestamps preserve event time, documented time, ingestion time, timezone/precision, and source when known.
- Every final finding cites source identifiers **and retrievable source locations**.
- Unsupported or ambiguous material is marked uncertain; never fabricate quotes, lab values, diagnostic claims, dates, or tool outcomes.
- Agent inference must be visibly distinct from hospital documentation and case ground truth.
- Store ground truth separately, inaccessible to runtime investigators; use only in evaluation fixtures.

## Suggested internal contracts (adapt to existing specs)
`InvestigationRun`, `PlanTask`, `ToolExecution`, `EvidenceItem`, `TimelineEvent`, `ContradictionCandidate`, `HypothesisAssessment`, `Finding`, `InvestigationReport`. Use `schema_version` and deterministic identifiers or persisted UUIDs. JSON serializable; validate using Pydantic.

## Events emitted to UI
`run.started`, `plan.created`, `tool.started`, `tool.succeeded`, `tool.failed`, `evidence.registered`, `timeline.updated`, `contradiction.detected`, `hypothesis.updated`, `verification.completed`, `report.ready`, `run.failed`. Each includes run ID, monotonically increasing sequence, timestamp, stage, and safe payload; do not leak hidden ground truth or unneeded PHI.

## Execution constraints
Refactor 05: baseline remains default. Adaptive execution uses internal
`schemas/planning.py`, `agents/runtime.py`, `orchestration/planner.py` and
`orchestration/supervisor.py`. Follow-ups require deterministic approval and a
scoped executor. Retain source/version/creator IDs in events, per-role budgets across
tasks, and explicit exhausted/failed limitations. No adaptive model mode exists:
the provider still proposes only candidates/hypotheses. Read the executable section
of `docs/multi-agent-architecture.md`.

Refactor 02: use `composition.build_engine` for local composition. The engine
requires ClinicalSource and InvestigationRuntime capabilities; specialists get
ToolExecutor only. Persistence commands/activity/findings/queries/recovery share
one InvestigationPersistence writer/CAS boundary. Do not create separate writer
locks or move external waits inside transactions when extending collaborators.

Bound tool calls, retries, input size, and execution duration. Prefer deterministic rule-based temporal checks before model interpretation. Use durable state or replayable events; demo reset seeds known synthetic cases and clears only run artifacts. Favor understandable FastAPI modules over excessive abstractions.

## Validation / definition of done
A seeded CASE-001 run discovers the intended timeline contradiction only by retrieving sources, displays intermediate tool actions, distinguishes contradiction from proven harm, verifies every final citation, and is repeatable without ground-truth leakage. Negative-control cases do not produce the same finding. Failures and missing data produce explicit uncertainty and useful UI status.

## Related skills
`investigation-planning.md`, `evidence-collection.md`, `timeline-reconstruction.md`, `contradiction-detection.md`, `hypothesis-generation.md`, `hypothesis-testing.md`, `evidence-linking.md`, `uncertainty-analysis.md`, `final-report-generation.md`.

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.
