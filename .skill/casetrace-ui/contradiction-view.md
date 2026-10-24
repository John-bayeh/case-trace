# Contradiction View Skill

## Purpose
Expose why two or more records are inconsistent and what was verified, without overclaiming causality.

## Model
Use backend finding ID, claim, contradiction type, compared source IDs and quoted/structured observations, their timestamp semantics, verification state, confidence label, and unresolved questions.

## Presentation
- Comparison columns: Source A vs Source B, independent metadata and clickable citations.
- Clearly separate **record conflict**, **possible explanation**, and **verified finding**.
- Show provenance, versions/amendments, missing evidence, and uncertainty before highlighting the dramatic conclusion.
- Treat conflicting times and ambiguous timezones as uncertainty, not automatic error.

## Interaction
Jump to timeline nodes; open both primary sources; show what the investigator checked and which evidence affected status.

## Tests
One missing source, more than two sources, conflicting amendments, date-only records, low confidence, disproven candidates.

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
