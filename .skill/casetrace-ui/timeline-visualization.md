# Timeline Visualization Skill

## Purpose
Display a longitudinal clinical history with explicit temporal ambiguity and source-linked events.

## Model
Consume typed events with stable event ID, event category, time semantics (occurrence, documentation, result, amendment), precision/timezone when known, provenance link, and optional finding associations.

## Display rules
- Default order by clinical occurrence time where known; make alternate timestamp basis selectable and clearly label it.
- Never silently use note creation time as encounter time.
- If only a date is known, show date-only and avoid arbitrary clock placement. If times disagree, preserve competing source values.
- Provide grouped lanes or tags for visits, labs, medications, imaging, referrals, notes.
- Highlight linked contradictory events without implying which is true.

## Interactions
Filter by category and date, jump from finding to relevant event, select event to open evidence panel, accessible list alternative to visual timeline.

## Performance
Virtualize long event histories where needed; paginate/filter on server when contract supports it; keep selected event stable across sort/filter.

## Tests
Out-of-order records, date-only timestamps, timezone transitions, equal timestamps, duplicates, missing event times, links to amended records.

## Shared implementation rules
- Use Next.js App Router, TypeScript, accessible semantic components, and the existing CASETRACE design system. Reuse the supplied HTML prototypes as visual references, not as runtime data sources.
- Honor `frontend-architecture.md`, `frontend-backend-contract.md`, `case-schema.md`, `agent-tools.md`, and `hospital-api.md` when available; those contracts override example names here. Do not fabricate API fields or silently rename contract keys.
- Render only records and tool events provided by the backend. Never create investigation findings in the browser, infer clinical conclusions, or read ground-truth answer keys.
- Every evidence-related link must resolve through stable case/patient/encounter/resource IDs to a source record, document page, or image; show a safe fallback if the target is unavailable.
- Show loading, empty, error, unauthorized, stale, and partial-result states. Preserve case scope across navigation; avoid leaking cached data between patients.
- Distinguish recorded clinical timestamps from ingestion, retrieval, and agent-execution times; label timezone and precision where necessary.
- Treat all cases as synthetic demo data. Add a conspicuous `SYNTHETIC DEMO — NOT FOR CLINICAL USE` label in clinical views and exported reports.
- Maintain keyboard navigation, meaningful focus states, accessible table headers, readable contrast, and reduced-motion support.

## Definition of done
- Component has typed inputs, meaningful states, responsive layout, and accessible interaction.
- Actions are connected to contract-backed handlers; no inert demo buttons or hardcoded claims.
- Unit/component tests cover state transitions and empty/error paths; at least one integration test checks evidence deep-linking and patient isolation.
