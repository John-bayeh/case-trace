# Backend Service Patterns

## Responsibility separation
- **Hospital service:** query records and enforce relationships and filters.
- **Investigation service:** create/retrieve run state and coordinate orchestrator.
- **Agent/tool adapter:** make actual tool calls, record inputs/outputs and errors.
- **Evidence service:** validate references, normalize timestamps, build verified source links.
- **Report service:** assemble findings only from validated evidence; state uncertainty.
- **Repository:** query or persist domain entities; no clinical interpretation.

## Example orchestration pseudocode
```text
start investigation(patient_id)
  → confirm patient exists
  → create investigation record (state=queued)
  → enqueue work and return investigation_id
run investigation
  → record state=running
  → query hospital tools for permitted patient scope
  → normalize into events without overwriting source records
  → identify potential conflicts and fetch supporting original records
  → verify each citation resolves to an existing source
  → write findings with confidence/limitations
  → persist report and terminal state
```
Use existing contracts for actual state names, orchestration boundaries, and event schemas. Do not assume a durable queue is required for a hackathon; a well-contained local execution worker is acceptable if reliable.

## Invariants
- Only evidence retrieved via permitted service/tool paths can support a final claim.
- Investigative reasoning must not change raw hospital source records.
- Assign stable IDs to findings and links; preserve run/version provenance.
- Distinguish claimed clinical time, source recorded time, and ingest time when available.
- Report partial progress honestly when some tools fail or records are absent.
- Avoid retrying non-idempotent operations blindly.

## Tests
Mock repositories and tools for unit tests; integration-test against seeded hospital data. Assert no unsupported finding survives verification, and failed tool calls are preserved in the investigation trace.

## Stack alignment

Use uv (`uv run` for application, migrations and tests) and the shared [stack policy](../../docs/development-stack.md). A service must materialize read results and close the session before inference/tool waits; audit-start and audit-result use separate short commits. The persistence service serializes bounded writes, checks versions and atomically commits state plus durable events. Never pass a session to an agent.
