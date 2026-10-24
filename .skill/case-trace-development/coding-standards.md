# Coding Standards

## Scope
Applies to all CASETRACE code and scripts. Layer-specific skills add detail.

## General
- Prefer straightforward, typed, modular implementations with single-purpose functions.
- Choose descriptive domain names: `encounter_id`, `recorded_at`, `evidence_refs`, `investigation_id`; avoid ambiguous `data` or `result` at module boundaries.
- Do not duplicate domain enums, status transitions, or validation schemas across packages without deliberate generation/mapping.
- Make IDs stable and opaque; never rely on array indices for record identity or citation links.
- Keep synthetic seed content separate from production code; never embed answer keys in UI bundles or APIs exposed to investigators.
- Isolate external effects (network, database, filesystem, model provider) behind explicit interfaces.

## TypeScript / Next.js
- Use strict TypeScript; avoid `any` and unchecked casts. Prefer `unknown` plus runtime narrowing for untrusted payloads.
- Type all public component props, API responses, and discriminated unions for async/investigation states.
- Use server rendering where appropriate; add `use client` only where interactivity requires it.
- Centralize API calls and transport-to-view-model conversion; do not scatter `fetch` and field transforms across components.
- Provide stable React keys based on record IDs, not list positions.

## Python / FastAPI
- Use Python type hints and Pydantic schemas for requests/responses; separate transport schemas from persistence models.
- Keep routers thin, services focused on use cases, and repositories focused on reads/writes.
- Dependency-inject database sessions, clients, and time sources to enable tests.
- Use UTC for canonical storage when possible; preserve original source timestamp and offset separately.
- Avoid mutable defaults, hidden global state, and blocking calls inside async routes.

## Data and observability
- Use documented schema migrations for persisted changes; do not modify historical clinical records in place.
- Log correlation IDs, operation names, timings, and sanitized error categories; avoid logging raw record bodies by default.
- Add request/investigation IDs to cross-service logs and agent tool results.
- Use deterministic sort order for timelines: clinical time, documented tie-breaker, stable record ID.

## Repository quality gate
Run the commands defined by the actual repository tooling (e.g., ESLint, `tsc --noEmit`, Ruff, Pytest, migration checks). Never claim a command ran if it did not. Add tests for every defect fix. Prefer small, coherent commits or patches.
