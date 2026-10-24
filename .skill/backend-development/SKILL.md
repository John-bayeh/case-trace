---
name: backend-development
description: 'Implement FastAPI services that expose the synthetic hospital, execute evidence-preserving investigation workflows, and serve typed APIs consumed by the Next.js frontend. Use for: API endpoints, dependency injection, hospital data retrieval, agent orchestration integrations, investigation sessions, report assembly, validation, and background/event delivery.'
---

# Backend Development Skill

## Purpose
Implement FastAPI services that expose the synthetic hospital, execute evidence-preserving investigation workflows, and serve typed APIs consumed by the Next.js frontend.

## When to use
API endpoints, dependency injection, hospital data retrieval, agent orchestration integrations, investigation sessions, report assembly, validation, and background/event delivery.

## Required context
Read backend architecture, `frontend-backend-contract.md`, `hospital-api.md`, `agent-tools.md`, and `case-schema.md` before editing interface behavior. Apply `api-patterns.md`, `service-patterns.md`, and the database skill.

## Architecture rules
- Refactor 02 composition lives in `app/composition.py` and FastAPI lifespan.
  Construct local engines with `build_engine`; inject clinical/assets/provider
  capabilities through `create_app` for tests. Keep HTTP repository/service
  factories in `app/api/dependencies.py`.
- Routers: HTTP auth/validation/serialization; services: domain use cases; repositories: persistence and retrieval; tool adapters: explicit, auditable calls.
- Preserve source record immutability; derivations and user annotations belong in separate storage.
- Do not give agent runtime direct access to hidden case ground truth.
- Every tool result must preserve source identifiers and retrieval status; agent assertions reference existing evidence.
- Use dependency injection for DB session, tool client, clock, agent provider, and event publisher.
- Support deterministic replay or stubbed model output for the demo without pretending it is live reasoning.

## Workflow
Review affected contracts → write schema/route tests → implement service and repository changes → ensure provenance and lifecycle logging → run targeted integration tests → update docs if contract changes.

## Definition of done
Request validation, correct statuses, well-defined errors, tests, traceable evidence, no leaked secrets, and frontend-compatible responses.

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.
