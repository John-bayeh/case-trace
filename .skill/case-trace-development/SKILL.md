---
name: case-trace-development
description: 'Coordinate development of CASETRACE: a synthetic-hospital, evidence-grounded AI clinical investigation prototype. This skill governs work spanning modules; more specific skills govern their respective layers. Use for: Use for feature planning, cross-layer changes, migrations, debugging, code review, integration, and agent handoffs. Load the relevant frontend, backend, and database skills before modifying those layers.'
---

# CASETRACE Development Skill

## Purpose
Coordinate development of CASETRACE: a synthetic-hospital, evidence-grounded AI clinical investigation prototype. This skill governs work spanning modules; more specific skills govern their respective layers.

## When to use
Use for feature planning, cross-layer changes, migrations, debugging, code review, integration, and agent handoffs. Load the relevant frontend, backend, and database skills before modifying those layers.

## Source-of-truth order
1. Repository `AGENTS.md` and the user's current request.
2. `frontend-backend-contract.md`, `case-schema.md`, `agent-tools.md`, and `hospital-api.md` for their respective interfaces.
3. Backend/frontend architecture specifications and `docs/casetrace-ui-design/` references.
4. Existing tests and implementation for details not specified elsewhere.

If sources disagree, identify the conflict, prefer explicit contract definitions, and make the smallest documented resolution. Do not silently invent endpoint shapes.

## Product invariants
- All patient identities, observations, media, and notes are **synthetic** and labeled accordingly. Never import real patient data into demo fixtures.
- Hospital records and agent-derived assertions are distinct; an AI conclusion must not overwrite an original record.
- Every cited assertion must link to an actual evidence ID and to its retrievable source (encounter, lab, medication, document, or image). Unsupported claims remain hypotheses.
- Record timestamps retain precision, timezone/offset, source, and ingestion metadata where available. Distinguish *event time* from *recorded time*.
- Agent tool calls execute against the simulated hospital API/service, not a hidden answer key. Keep ground truth inaccessible to runtime investigative agents.
- The demo must be deterministic/replayable under a fixed dataset and configuration, without fabricating completed tool calls.
- The system is investigation support, not an autonomous diagnostic or treatment system. No real-patient deployment claims.

## Execution workflow
1. Read affected contracts and existing files; outline expected inputs, outputs, and integration surfaces.
2. Implement a vertical slice: data model → service/API → UI → tests, when feasible.
3. Validate schema and test fixture compatibility; add migrations or adapters rather than breaking existing cases.
4. Run relevant lint, type checks, automated tests, and an end-to-end evidence drill.
5. Report changed files, commands executed, outcomes, assumptions, and remaining limitations.

## Required engineering behavior
- Avoid unrelated refactors and new dependencies without rationale.
- Keep logic discoverable through bounded modules; avoid oversized orchestrators and components.
- Validate at trust boundaries; give actionable errors without leaking sensitive internals.
- Do not silently catch exceptions, fabricate data, or return successful-looking empty results when a required dependency failed.
- Prefer understandable implementation and demo reliability over distributed infrastructure complexity.

## Definition of done
Feature follows the applicable contract, handles empty/loading/error states, passes relevant tests, preserves citation provenance, remains reproducible with synthetic fixtures, and has a concise integration note.

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.
