# UI State Patterns

## Ownership
- **URL state:** patient ID, encounter ID, investigation ID, selected report section, supported filters/deep links.
- **Server state:** patient list, records, investigation status, evidence, tool-event log, report; keep cache consistent with backend.
- **Local state:** open panels, selected tabs, nonpersistent form drafts.
- **Derived state:** ordered timeline, grouped records, aggregate counters; derive from canonical data rather than duplicating mutable stores.

## Async state machine
Model `idle → loading → success | empty | partial | error`. Do not collapse `empty`, `partial`, and `error`. Investigation lifecycle should follow actual backend states, e.g. `created → queued → running → completed/failed/cancelled`, but use the contract's exact enum names.

## Event/polling behavior
- Prefer backend-defined stream or polling semantics; do not invent events or timestamps.
- Deduplicate tool events by stable event ID and order by sequence or canonical timestamp + ID.
- On reconnect, request authoritative state and backfill from cursor if API supports it.
- Show reconnecting/disconnected indicator; do not mark workflow completed until backend says so.
- Cancel listeners/polls on unmount and investigation change; prevent stale response overwrites.

## Evidence navigation
Keep selected `evidence_ref` (or contractual equivalent) in route/search state when deep links are required. Click report claim → resolve evidence → open source view → highlight cited field. If target missing, show explicit unresolved-reference state rather than switching to unrelated evidence.

## Forms, errors, loading
Validate client input for convenience, but rely on server validation. Use disabled/loading state to prevent accidental duplicate commands. Retry idempotent reads; avoid blind retries of investigation-creation requests unless idempotency keys are supported. Use skeletons for initial load and unobtrusive pending indicators for refresh.

## Verification
Test refresh during active investigation, rapid switching between patients, network interruption, duplicate events, unknown statuses, partial source availability, and navigation directly to a citation deep link.
