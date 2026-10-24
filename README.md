# CASETRACE

CASETRACE is an AI clinical investigation prototype that reconstructs medical mysteries from longitudinal synthetic patient records. It is designed to connect evidence across encounters, reconstruct timelines, identify contradictions, and produce findings that link back to their original sources.

The initial demonstration focuses on a timeline contradiction that becomes visible only when multiple clinical records are connected.

## Project status

The [Refactor 01 architecture audit](docs/refactoring/01-current-state-audit.md)
records the current implementation, executed baseline checks and remaining gaps.
Its [compatibility decisions](docs/refactoring/04-contract-compatibility.md) reconcile
historical examples; the [backlog](docs/refactoring/05-refactoring-backlog.md)
defines the proposed incremental refactoring program.

The foundation and synthetic hospital are implemented. Phase 3 adds a controlled,
tool-backed investigation worker, source verification, persisted findings/reports,
REST/SSE APIs and a typed client. Phase 4 connects the browser dashboard, patient
chart, live investigation workspace, original-source evidence and printable report.
See [Phase 4 development](docs/phase-4-development.md) and its
[validation report](docs/phase-4-report.md). CASE-001 runs in explicitly labelled deterministic
rules mode; optional Gemini proposals require configured credentials/model. See
[Phase 3 development](docs/phase-3-development.md) for commands and limitations.

## Intended experience

1. Select a synthetic patient and explore their hospital records.
2. Start an investigation across the available clinical history.
3. Follow actual record retrieval and investigation activity.
4. Inspect reconstructed timelines, contradictions, and verified evidence.
5. Open the source records supporting each report finding.

## Planned architecture

| Component | Technology and responsibility |
| --- | --- |
| Web application | Next.js, TypeScript, Tailwind CSS, shadcn/ui; hospital and investigation workspaces |
| API | Python 3.12+, FastAPI, Pydantic v2; hospital APIs and investigation services |
| Persistence | SQLite, SQLAlchemy 2, Alembic |
| Investigation execution | Specialized agents, clinical retrieval tools, asyncio workers |
| Live activity | Server-Sent Events (SSE) |
| Package management | pnpm (web), uv (API) |
| Local infrastructure | Local processes preferred; optional Docker Compose for API/web |

Agents retrieve clinical information through defined tools and hospital services, rather than accessing the database or raw case files directly. Models propose findings; deterministic backend code verifies source references, timestamps, and clinical values. Evaluation ground truth must remain isolated from agents and runtime interfaces.

## Repository layout

```text
AGENTS.md           Repository instructions and architectural rules
docs/               Product requirements, architecture, contracts, and plans
ui-design/          Empty design placeholders; usable references are under docs/casetrace-ui-design/
apps/api/           Backend application scaffold
apps/web/           Frontend application scaffold
data/cases/         Synthetic case folders, CASE-001 through CASE-010
data/assets/        Supporting synthetic case assets
scripts/            Development, validation, and data tooling scaffold
tests/              Test scaffold
```

Some documentation files and directories are placeholders. Empty directories are not tracked by Git until files are added.

## Documentation

Start with [repository guidance](AGENTS.md) and the [product requirements](docs/PRD.md).

- Architecture: [frontend](docs/frontend-architecture.md), [backend](docs/backend-architecture.md), and [frontend/backend contract](docs/frontend-backend-contract.md).
- Clinical data: [case schema](docs/case-schema.md), [hospital API](docs/hospital-api.md), and [database schema](docs/database-schema.md).
- Investigations: [agent tools](docs/agent-tools.md), [multi-agent architecture](docs/multi-agent-architecture.md), [state machine](docs/investigation-state-machine.md), and [evidence contract](docs/evidence-contract.md).
- Delivery: [implementation plan](docs/implementation-plan.md), [evaluation plan](docs/evaluation-plan.md), and [demo runbook](docs/demo-runbook.md).
- Design: [UI design and tokens](docs/casetrace-ui-design/ui-design.md) and [HTML prototypes](docs/casetrace-ui-design/index.html). The files under `ui-design/` are empty placeholders.

## Development

Read the relevant architecture and contracts before implementing a feature. Follow the implementation plan and preserve evidence provenance and distinct timestamp meanings throughout the system.

See [local development](docs/local-development.md) for executable WSL setup/run/test commands and [development stack and SQLite operations](docs/development-stack.md) for storage policy. Lockfiles live in each application; use frozen/locked installs. Skills live under `.skill/<name>/SKILL.md`.

SQLite runtime state belongs in `data/runtime/casetrace.db`, resolved against a central absolute root rather than the shell's working directory. WAL, foreign keys and a busy timeout are required. Preserve source assets outside the database and evaluator keys outside runtime access. The [demo runbook](docs/demo-runbook.md) defines planned deterministic reset and recovery.

Use synthetic case data for this prototype. Keep credentials and local environment values out of version control; `.env.example` is reserved for documented placeholder values.

## Phase 5 validation

See [evaluation and safe demo operations](docs/phase-5-development.md), [release-readiness assessment](docs/phase-5-report.md), and the [four-minute demo runbook](docs/demo-runbook.md). Rules-mode API/browser runs are verified; live LLM execution and clinical expert review remain unverified. The dedicated reset never targets the normal development database.


### Frontend architecture (Refactor 07)

Existing routes now compose domain modules in `apps/web/features/`. Shared shell
and UI states live in `components/`; typed clients, scoped reads, validation and
SSE remain in `lib/`. No new clinical or inventory routes are implied.
See [frontend refactor report](docs/refactoring/11-frontend-architecture-refactor-report.md)
for migration mapping, test results, the retained server-state strategy and
Refactor 08 prerequisites. Run `pnpm typecheck`, `pnpm lint`, `pnpm test` and
`pnpm build` from `apps/web` (`pnpm.cmd` in Windows PowerShell).
