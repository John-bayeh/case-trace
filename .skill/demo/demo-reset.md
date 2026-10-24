# Demo Reset and Repeatability

## Purpose
Return CASETRACE to a known clean presentation state while keeping source records immutable and audit handling explicit.

## Prerequisites
A versioned synthetic dataset, validated seed scripts, environment-specific database/asset configuration, demo tenant ID, and a documented procedure for retaining run logs. Reset must be restricted to synthetic demo environments.

## Never do
- Reset production or real hospital data.
- Execute a broad deletion without demo-environment and tenant checks.
- Remove seed originals or evaluator ground truth by accident.
- Erase investigation/audit logs silently; archive or rotate them per demo policy.
- Assume a command exists: locate the implemented reset script first.

## Procedure
1. Verify `APP_ENV=demo` (or the project's authoritative equivalent) and correct tenant; refuse otherwise.
2. End active runs and capture their statuses; archive required logs and export diagnostics.
3. Clear only generated demo investigation state: temporary sessions, tool-run cache, derived timelines, generated reports, and ephemeral event streams scoped to the demo tenant.
4. Restore CASE-001 and optional backups from the versioned synthetic fixture manifest using idempotent seed tooling.
5. Verify SQLite indexes and derived projections if used; confirm storage paths and content checksums.
6. Verify seeded patient count, encounter and document counts, evidence IDs, and original artifact availability against manifest values (not invented hard-coded numbers).
7. Check hospital endpoint health and agent-tool auth/read permissions.
8. Launch a smoke investigation, verify tool execution and citation opening; then clear this smoke run to leave clean initial UI state.
9. Record reset metadata: time, dataset version, seed checksum, operator, result, and retained log location.

## Suggested command interface (illustrative; implement and document before use)
```bash
# Never run against production; replace with actual project commands
uv run --project apps/api python scripts/demo_reset.py --tenant demo --case CASE-001 --dry-run
uv run --project apps/api python scripts/demo_reset.py --tenant demo --case CASE-001 --confirm
uv run --project apps/api python scripts/demo_preflight.py --tenant demo --case CASE-001
```
Commands above are proposals, not claims that they already exist.

## Automated acceptance criteria
- Re-running reset produces the same fixture state (idempotent).
- Seed data and asset checksums match the frozen manifest.
- Investigation starts with no leaked old activity or cached conclusions.
- Historical audit/run data is archived or retained according to configured policy.
- Two consecutive full demo runs and resets pass without manual database edits.

## Stack alignment

Follow the [demo runbook](../../docs/demo-runbook.md) and [SQLite operations](../../docs/development-stack.md). Stop workers and close connections before maintenance; archive audits and a consistent backup. Never remove a live DB/WAL/SHM or modify canonical fixtures. Rebuild imported records only through reviewed migrations and validated idempotent seeds; verify hashes and source IDs.

## Implemented Phase 5 command

Use `scripts/demo_reset.py --database <absolute dedicated data/runtime/demo/casetrace-demo.db> --dry-run`, then `--confirm --offline` with the dedicated API stopped. The authoritative environment equivalent is development mode plus this exact target allowlist; APP_ENV=demo is not a supported application enum. Existing data is backed up, active runs are refused, and only investigation-domain rows are cleared in dependency order. See [Phase 5 operations](../../docs/phase-5-development.md). Offline acknowledgment is an operator prerequisite, not an enforced OS maintenance lock.
