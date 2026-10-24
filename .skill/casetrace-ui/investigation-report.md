# Investigation Report UI Skill

## Purpose
Render a reviewable and exportable, source-backed investigation report for a synthetic case.

## Sections
Run metadata + synthetic-use notice; executive finding; timeline narrative; verified discrepancies; evidence matrix; alternative explanations; uncertainty/limitations; agent audit summary; source bibliography.

## Rendering
Use backend report as authoritative; every material claim displays citation IDs that open exact hospital sources. Distinguish `verified`, `supported`, `possible`, and `unresolved` using actual backend statuses. Do not use a client-side LLM to embellish.

## Export
Prefer server-generated PDF/download URL where contracted, preserving source IDs and disclosure. Otherwise offer accessible print with stable citation text. Verify export authorization and patient/run match.

## States
Draft, generating, ready, failed, superseded; show actual generation status and version. Incomplete evidence yields an explicitly partial report, never a final-looking certified diagnosis.

## Tests
Citation target integrity, report/version mismatch, missing referenced artifact, print readability, synthetic disclaimer in export, keyboard navigation.

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
