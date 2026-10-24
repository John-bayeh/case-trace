---
name: casetrace-ui
description: 'Build a credible hospital-facing investigation interface that makes the AI investigation inspectable, not merely dramatic. Use for: Any task touching investigation screens, patient records, evidence references, timeline rendering, agent activity, contradiction comparison, or final reports.'
---

# CASETRACE UI — Master Skill

## Purpose
Build a credible hospital-facing investigation interface that makes the AI investigation inspectable, not merely dramatic.

## When to use
Any task touching investigation screens, patient records, evidence references, timeline rendering, agent activity, contradiction comparison, or final reports.

## Screen model
1. Hospital dashboard → patient search → patient record.
2. Launch an investigation for a scoped patient/case.
3. Workspace streams actual backend events and progressively presents timeline, evidence, and hypotheses.
4. Investigator opens source documents, compares disputed facts, and reviews the final report.

## Layout and navigation
- Primary shell: patient identity + synthetic-data banner, investigation status, record navigation.
- Workspace: timeline and findings main area; evidence drawer; agent activity panel; responsive tabs on narrow screens.
- Keep record IDs in route params and selected evidence in shareable URL state when safe.
- Reconcile streaming events with fetched snapshots by stable event ID and server sequence to avoid duplicate entries.

## Ownership boundaries
- Hospital API provides canonical records; investigation API provides statuses, traces, findings, and reports.
- Frontend owns display-only selection, filters, tabs, and drawer state.
- All clinical analysis and evidence scoring remain on backend.

## Workflow
Inspect design prototypes and contracts → identify types/endpoints → build typed data hooks → implement accessible views → wire source navigation → test with CASE-001 and non-mystery cases.

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

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.

## Refactor 07 source navigation

Use `features/evidence/navigation.ts` for source selections and anchor grouping,
`features/evidence/hooks/use-evidence-selection` for identifier-only URL state,
and `use-source` for patient-scoped retrieval. Source panels consume these
boundaries. Original optional `char_start`/`char_end` use Python Unicode code-point
indices: highlight only when the current field substring equals the exact quote.
Missing offsets use the field-level fallback; mismatched spans show an error.
Never infer PDF pages. Use shared shell/navigation, environment banner and UI states.
See `docs/refactoring/11-frontend-architecture-refactor-report.md` for deferred screens.
