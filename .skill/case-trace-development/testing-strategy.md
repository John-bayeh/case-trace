# Testing Strategy

## Goal
Tests must demonstrate correct application behavior **and** correct evidence provenance. Plausible text alone does not count as a correct investigation.

## Test layers
1. **Unit:** parsing, temporal comparison, evidence-reference validation, reducer transitions, normalization.
2. **Contract:** API request/response and tool schemas vs authoritative Markdown contracts; assert validation errors.
3. **Repository/integration:** seeded hospital database, patient-to-encounter-to-record joins, source retrieval, pagination, filter ordering.
4. **Workflow:** investigation uses hospital tools, assembles evidence, exposes agent actions, identifies candidate contradiction, validates citations.
5. **E2E/UI:** search patient, open encounter, start investigation, view timeline, inspect evidence, open report, reset demo.
6. **Safety/robustness:** ambiguous timestamps, conflicting entries, missing images, failed service, malicious text in synthetic notes, nonexistent IDs.

## Synthetic fixture rules
- Use CASE-001 as the high-fidelity golden workflow, and at least one negative/control case with no supported contradiction.
- Keep ground-truth answer keys in test-only fixtures, never in agent runtime context.
- Seed with deterministic IDs, stable timestamps, and fixed model responses when testing orchestration.
- Assert required clues cite real source record IDs; test that intentionally dangling citations fail verification.
- Treat contradiction detection as evidence comparison, not brittle expected prose matching.

## Example acceptance checks
- Each citation dereferences to the expected source and quoted segment/field.
- Timeline ordering is stable across timezone offsets and same-time events.
- A search returning zero patients shows empty state, not server error.
- Missing lab pages never become the assertion “lab normal.”
- Agent trace records actual tool names, arguments metadata, outcome, and durations.
- Reset returns the same case and demo state without altering immutable source records.

## Running and reporting
Execute targeted checks during changes and whole-project checks before demo delivery. Report exact commands, pass/fail/skipped status, fixture version, and nondeterministic dependencies. If an external model is unavailable, run a deterministic stub and label the limitation.

## Definition of done
Tests cover happy path, at least one edge/failure mode, provenance verification, and regression for any bug fixed.

## Stack alignment

Planned commands and CI lockfile gates are in [development stack](../../docs/development-stack.md). Use `uv run pytest` for configured backend tests and `pnpm test` only once defined in the frontend manifest. Use isolated file-backed SQLite per test/worker; in-memory tests skip WAL. Cover migration, FK settings on new connections, UTC round trips, lock contention, version conflicts, idempotent results, reset and backup recovery.
