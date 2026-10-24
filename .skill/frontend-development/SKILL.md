---
name: frontend-development
description: 'Build the CASETRACE Next.js + TypeScript interface for simulated hospital operations and transparent AI investigation. Use for: Any work on dashboard, patient record, encounters, labs, medication history, document or imaging viewers, timeline, agent trace, contradiction view, and investigation report.'
---

# Frontend Development Skill

## Purpose
Build the CASETRACE Next.js + TypeScript interface for simulated hospital operations and transparent AI investigation.

## When to use
Any work on dashboard, patient record, encounters, labs, medication history, document or imaging viewers, timeline, agent trace, contradiction view, and investigation report.

## Required context
Read `ui-design/ui-design.md`, `ui-design/design-system.md`, relevant HTML prototypes, `frontend-architecture.md` and `frontend-backend-contract.md` (using repository names if different). Consult `component-patterns.md` and `ui-state-patterns.md` for implementation.

## UX principles
- Clearly separate **hospital source record** from **agent interpretation**.
- Make each important report claim clickable to a real source record/field; never display decorative fabricated citations.
- Show whether an agent is queued, running, succeeded, failed, or blocked; tool activity should reflect real backend events.
- Support realistic clinical density without hiding essential timestamps, units, status, or author/source metadata.
- Maintain an explicit **SYNTHETIC DEMO DATA** indication in hospital and report contexts.
- Preserve usability with keyboard navigation, semantic labels, responsive layouts, focus indicators, and accessible status changes.

## Implementation workflow
1. Identify route/view and the exact API contract.
2. Build typed data boundaries and components without mocked business logic in production paths.
3. Implement loading, empty, partial, error, and success states.
4. Add evidence linking and stable navigation between timeline, source record, and report.
5. Test visual layout and E2E flow using seeded CASE-001 fixtures.

## Forbidden shortcuts
Do not hard-code contradiction conclusions, tool activity, or “live” progress animation unrelated to actual backend state. Do not expose hidden ground truth. Do not make a static document appear to be a working investigation.

## Done when
Matches UX reference, typechecks, handles server errors, is keyboard-operable, and resolves evidence links to actual data.

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.
