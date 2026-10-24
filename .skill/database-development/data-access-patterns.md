# Data Access Patterns

## Repository interfaces
Prefer explicit operations such as `get_patient`, `list_encounters`, `list_lab_results`, `get_document`, `list_medications`, `list_investigation_events`, and `resolve_evidence_reference`. Match `hospital-api.md` terminology and data scopes.

## Query behavior
- Require patient scoping for record retrieval; avoid accidental cross-patient joins.
- Use bound parameters or ORM query APIs, never string-concatenated SQL with user input.
- Paginate large collections. Sort deterministically by clinical timestamp and record ID.
- Avoid N+1 queries in patient chart and investigation timeline; preload only required relationships.
- Use indexes for patient ID, encounter ID, relevant timestamp, document/record ID, and investigation ID based on query plans.
- Return explicit not-found/error cases rather than silent fallbacks.
- Fetch original record or field for citation verification; do not trust UI-provided excerpt as authoritative.

## Transactions and persistence
- Write source fixture bundles atomically where feasible.
- Use a transaction for multi-row investigation writes that must stay consistent.
- Keep clinical source rows immutable after seed, unless a separate audited correction workflow is explicitly designed.
- Persist tool-call audit records and report/citation links with stable IDs.
- Introduce migrations for schema changes; do not rely on auto-create behavior outside local disposable tests.

## Synthetic dataset import
1. Validate schema and required relationships before writing.
2. Confirm all referenced encounter and patient IDs exist.
3. Verify timestamps and expected clinical ordering while retaining intentional contradictions as evidence.
4. Validate media paths, hashes if present, and document references.
5. Load with deterministic IDs and produce counts/warnings.
6. Keep answer keys in a separate testing namespace unavailable to runtime agents.

## Tests
Cross-patient isolation, encounter integrity, same-time ordering, duplicate seed behavior, missing foreign keys, unresolved media, pagination consistency, and evidence reference resolution.

## Stack alignment

Use [SQLite operations](../../docs/development-stack.md) for absolute paths, every-connection foreign keys and busy timeout, file WAL, portable UUID/JSON/enum/UTC types, Alembic batch migrations and isolated test files. Use a session per operation, explicit short transactions and version-guarded writes; no row locks. Test stale writes, duplicate retry results, FK enforcement and UTC restoration.
