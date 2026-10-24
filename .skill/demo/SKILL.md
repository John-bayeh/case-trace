---
name: demo
description: 'Deliver a reproducible, high-impact, evidence-verifiable demo of CASETRACE investigating a fictional patient''s longitudinal hospital records. This skill governs demonstration orchestration, not clinical decision making. Use for: Use while preparing or running a hackathon demo, testing the end-to-end scenario, or resetting a demonstration environment. Read the specific subskill for each step.'
---

# CASETRACE Demo Operations Skill

## Purpose
Deliver a reproducible, high-impact, evidence-verifiable demo of CASETRACE investigating a fictional patient's longitudinal hospital records. This skill governs demonstration orchestration, not clinical decision making.

## When to use
Use while preparing or running a hackathon demo, testing the end-to-end scenario, or resetting a demonstration environment. Read the specific subskill for each step.

## Authoritative references
Follow `AGENTS.md`, `case-schema.md`, `agent-tools.md`, `hospital-api.md`, `frontend-backend-contract.md` and implemented endpoints. If a document is missing or disagrees, inspect the actual implementation and reconcile explicitly; never invent an API contract.

## Demo promise
CASE-001 is the primary timeline-contradiction case. The audience should see: a plausible patient chart; genuine, observable retrieval tool calls; an assembled chronology; an important contradiction; both original records; an evidence-linked report with uncertainty. No hidden answer-key access by investigation agents.

## Inputs
- Case ID and synthetic dataset version/checksum
- Hospital API base URL and demo tenant
- Investigation agent configuration and model availability
- Demo-mode configuration (live or explicitly labeled recorded fallback)
- Verified seed manifest, expected evidence identifiers, and evaluator-only ground truth

## Outputs
- Deterministic demo manifest and preflight results
- Read-only investigation run with tool/event logs
- Evidence-backed findings and report
- Recorded demo quality checklist and reset confirmation

## Mandatory rules
1. Use **synthetic** data only; unmistakably label the system and artifacts as demonstrations, not actual medical records.
2. Ground every assertion in source records or label it as a hypothesis. Never fabricate citations, records, timestamps, or a successful tool call.
3. Agent-side execution must not access evaluator-only ground truth or use an undisclosed precomputed conclusion.
4. Expose real tool execution states: queued, running, succeeded, failed, and retrying, as actually reported.
5. Never mutate original case records during an investigation. Separate investigation results and logs from source data.
6. Do not present an unvalidated numerical confidence score as a medical probability.
7. Do not expose secrets, local paths containing credentials, or other tenants' records.
8. Require an explicit distinction between live execution and replay/fallback modes.

## Workflow
1. Select case with `demo-case-selection.md`.
2. Execute preflight: dataset integrity; hospital service; retrieval endpoints; asset routes; agent tool bindings; clock/time zone; database migrations; render tests.
3. Walk through `investigation-flow.md`; capture actual events in order.
4. Present `wow-moment.md` with original evidence on screen.
5. Apply `failure-recovery.md` only if necessary, disclose fallback modes.
6. Run `demo-reset.md` and confirm a second run works without manual repair.

## Forbidden shortcuts
Hard-coded tool output disguised as live; scripted contradictory findings unrelated to stored records; manual edits to source documents mid-run; hiding retrieval errors; erasing audit logs to make the demo look successful; using real patient identifiers.

## Validation / definition of done
Two consecutive clean runs from a known seed produce the same core finding and citations; original records open at the cited spans; a failed network/model dependency has a clear documented contingency; reset does not destroy source-case assets.

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.
