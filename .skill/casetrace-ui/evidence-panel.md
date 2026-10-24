# Evidence Panel Skill

## Purpose
Make any finding auditable through an original, versioned hospital source.

## Inputs / outputs
Inputs: evidence references, excerpt/location pointers, source metadata and retrieval status. Output: source inspection panel with visible citation linkage.

## Required sections
- Citation summary: evidence ID, resource type, patient/encounter IDs, collected/recorded time, source version, cited claim.
- Original-source viewer: structured record, document with page/section anchor, or synthetic image with report linkage.
- Context: nearby results/notes when available; provenance and amendment trail without substituting new values for historical ones.

## Interaction
Click citation → resolve evidence reference via API → verify case/patient ownership → open record → highlight exact quote/field/region if source locator is valid.
Use side-by-side view for multiple pieces, with clear source boundaries.

## Failure rules
Missing source or invalid locator: label **Source unavailable / anchor unavailable**; show supplied metadata and do not imply verification. Excerpts are escaped; never render untrusted document HTML.

## Tests
Citation opens correct encounter and document/page; malformed IDs do not expose other patients; amended versions remain distinguishable; loading/error remain understandable.

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
