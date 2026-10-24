# CASETRACE - Stack alignment completion report

Date: 2026-10-20. Scope: documentation, development skills and existing root configuration examples only. No application features, dependencies, clinical cases or UI prototypes were created or changed. Starting Git working tree was clean; no changes were staged or committed.

## A. Files modified or added

The following inventory includes every changed file, including this report. Paths under `.skill/` are the existing installed skills; the requested `skills/` tree and separate validation skill do not exist, so no duplicate structure was created.

| File | Change |
| --- | --- |
| `.env.example` | Planned SQLite URL, path convention, timeout, API/frontend settings and secret placeholders. |
| `.gitignore` | Runtime database directory, SQLite database files and WAL/SHM/journal sidecars; removed unused server database volumes. |
| `.skill/_bundle-readmes/CASETRACE-casetrace-ui-skills/README.md` | Correct installed .skill paths, uppercase SKILL.md and AGENTS.md references. |
| `.skill/_bundle-readmes/CASETRACE-demo-skills/README.md` | Correct installed .skill paths, uppercase SKILL.md and AGENTS.md references. |
| `.skill/_bundle-readmes/CASETRACE-development-skills/README.md` | Correct installed .skill paths, uppercase SKILL.md and AGENTS.md references. |
| `.skill/_bundle-readmes/CASETRACE-hospital-system-skills/README.md` | Correct installed .skill paths, uppercase SKILL.md and AGENTS.md references. |
| `.skill/_bundle-readmes/CASETRACE-investigation-skills/README.md` | Correct installed .skill paths, uppercase SKILL.md and AGENTS.md references. |
| `.skill/_bundle-readmes/CASETRACE-synthetic-case-generation-skills/README.md` | Correct installed .skill paths, uppercase SKILL.md and AGENTS.md references. |
| `.skill/backend-development/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/backend-development/service-patterns.md` | uv commands, separate audit commits and controlled state/event persistence. |
| `.skill/case-trace-development/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/case-trace-development/testing-strategy.md` | Planned uv/pnpm checks and isolated SQLite/UTC/concurrency/recovery tests. |
| `.skill/casetrace-ui/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/database-development/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/database-development/data-access-patterns.md` | Portable SQLite types, connection policy, sessions, guarded writes and focused tests. |
| `.skill/demo/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/demo/demo-reset.md` | uv invocation, SQLite-compatible projections, quiescent maintenance, backup and source preservation. |
| `.skill/evidence/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/evidence/provenance.md` | Atomic provenance/finding/event persistence and idempotent retry links. |
| `.skill/frontend-development/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/hospital-system/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/investigation/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `.skill/investigation/evidence-collection.md` | Separate retrieval/audit commits, no external waits in transactions, guarded persistence. |
| `.skill/synthetic-case-generation/SKILL.md` | Route setup/persistence work to finalized stack policy; preserve responsibilities and contracts; fix existing authority/path guidance where applicable. |
| `AGENTS.md` | Approved stack, shared operational policy, actual skill location, API/web-only Docker diagram and SQLite rules. |
| `Makefile` | Comments identify planned command reference; no nonexistent executable targets. |
| `README.md` | Stack, package managers, planned workflow links, runtime location and explicit missing evidence contract. |
| `docker-compose.yml` | Document future optional API/web services, writable runtime mount and evaluator isolation; no invented runnable deployment. |
| `docs/PRD.md` | Finalized stack and storage diagram; existing feature scope preserved. |
| `docs/agent-tools.md` | SQLite boundary/testing terminology, separate audit commits and short repository reads. |
| `docs/backend-architecture.md` | SQLite system of record and async/uv session and transaction policy reference. |
| `docs/case-schema.md` | Canonical/generated/imported/runtime/evaluation separation and immutable source policy. |
| `docs/database-schema.md` | Portable DDL and types, UTC, logical domains, file/service security and guarded updates; entity catalog retained. |
| `docs/demo-runbook.md` | New planned startup, validation/seed/reset, data separation, preflight, backup/recovery and honest demo procedure. |
| `docs/development-stack.md` | New shared stack/toolchain/command policy and complete SQLite operational requirements, with primary technical references. |
| `docs/evaluation-plan.md` | Isolated file-backed SQLite, concurrency/UTC/migration/recovery checks and actual document filename. |
| `docs/frontend-architecture.md` | pnpm, planned toolchain/scripts/lockfile reference; existing UI choices preserved. |
| `docs/frontend-backend-contract.md` | SQLite environment example and stack reference; routes and structured examples preserved. |
| `docs/hospital-api.md` | SQLite repositories/testing/seeding, bounded read sessions and portable text-search guidance. |
| `docs/implementation-plan.md` | Five delivery phases with task/gate IDs retained; stack-specific foundation, commands, roles and first coding slice. |
| `docs/investigation-state-machine.md` | SQLite guarded claims, atomic state/event commits and actual document filename; state vocabulary preserved. |
| `docs/multi-agent-architecture.md` | SQLite persistent state and controlled concurrent result persistence; agent roles preserved. |
| `docs/stack-alignment-report.md` | Completion inventory, decisions, consistency classification, validation evidence, remaining issues and next implementation task. |

`.editorconfig` exists but is empty and remains unchanged. The current UI design placeholders under `ui-design/` are also empty and unchanged; existing HTML prototypes and design documents under `docs/casetrace-ui-design/` remain untouched.

## B. Final technology stack

| Layer | Final choice |
| --- | --- |
| Frontend | Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui, pnpm |
| Backend | Python 3.12+, FastAPI, Pydantic v2, uv |
| Database/ORM | SQLite, aiosqlite, SQLAlchemy 2.x asyncio |
| Migrations | Alembic |
| Execution/activity | Existing controlled multi-agent architecture, asyncio workers, SSE |
| Lockfiles | Planned `apps/web/pnpm-lock.yaml` and `apps/api/uv.lock` |

There are no application manifests, version pins, lockfiles, migrations or test scripts yet. Node.js 24 LTS + pnpm 10.x and Python 3.12 are documented bootstrap baselines, subject to compatibility checks with the selected framework versions; exact patches and the uv version must be pinned at bootstrap. All application commands are explicitly planned. No dependency installation was performed.

## C. Architectural decisions

- Central settings will resolve relative database and asset paths against a stable absolute root, not shell working directory. Default SQLite input is `sqlite+aiosqlite:///./data/runtime/casetrace.db`; settings convert it to an absolute URL. API, workers, Alembic, seed tooling, Docker and tests use the same resolver and connection policy.
- File databases use WAL; every connection enables foreign keys and a configurable busy timeout (default 5000 ms). Startup creates the runtime parent directory; application lifespan owns engine disposal. In-memory tests skip WAL.
- SQLite remains a single-writer database. One API process with in-process asyncio workers uses bounded short persistence critical sections, per-operation sessions, version/status guards and unique retry/result keys. Inference and external tool waits occur outside transactions. State changes and durable events commit atomically before streaming.
- Existing entities and logical hospital/investigation domains remain. UUIDs, JSON, enums and UTC instants use portable SQLAlchemy conventions. SQLite file permissions and service boundaries replace server roles/schemas; evaluator answers stay physically outside runtime access. No source-record mutation or answer-key import is permitted.
- Alembic handles persistent schema changes, including reviewed batch recreation where necessary. File-backed tests isolate each worker. Backups use a consistent SQLite snapshot or stopped/checkpointed connections; deterministic resets preserve canonical cases/assets and archive audit data. Fixtures reconstruct clinical imports, not lost historical investigations.
- Local development is preferred. Compose remains a documented scaffold until application Dockerfiles exist; planned deployment has API/web only, a persistent writable runtime mount and approved read-only source/asset mounts. It must not share one writable DB across independent app replicas.

Full operational details and primary technical sources are in [development stack](development-stack.md); deterministic maintenance is in the [demo runbook](demo-runbook.md).

## D. Consistency audit

Repository-wide search covered tracked and hidden skill/configuration files, excluding `.git`. Counts below are before migration versus the completed migration immediately before this report was added; occurrences in this audit report are explanatory, intentionally retained references.

| Search term/category | Before | After | Classification |
| --- | ---: | ---: | --- |
| PostgreSQL / Postgres, case insensitive whole words | 53 | 4 | Updated all active architecture/diagram/test instructions, including the Docker database service line. Four occurrences remain only in shared policy comparisons and future migration guidance; intentionally retained. |
| asyncpg | 1 | 0 | Updated the database URL to aiosqlite. |
| psycopg | 0 | 0 | Not applicable; no driver configuration exists. |
| DATABASE_URL | 2 | 4 | Updated URL example; retained backend-only secrecy rule; added consistent shared policy and environment example. |
| pip install | 0 | 0 | Not applicable; no recommended workflow existed. |
| requirements.txt | 0 | 0 | Not applicable; dependency workflow now explicitly uses pyproject.toml/uv.lock. |
| Poetry | 0 | 0 | Not applicable. |
| npm | 1 | 1 | Intentionally retained `.npm/` cache ignore; not a development command. |
| Yarn | 0 | 0 | Not applicable. |
| package-lock.json / yarn.lock | 0 | 0 | Not applicable; no lockfiles exist. |
| Docker database services | One `postgres` line in AGENTS diagram | None active | Updated diagram; actual Compose was empty, so there was no implemented service to remove. |

All ten skill entrypoints link to one maintained stack reference. Six bundle READMEs now use actual installed paths. Document filename casing was aligned and all actual relative Markdown links checked; no files were renamed or deleted. Public contract routes, IDs, enum values and structured payload examples were preserved. The implementation plan previously deferred specialist roles; its wording now follows the existing authoritative controlled agent pipeline rather than weakening it.

## E. Validation and remaining issues

Executed checks:

- `git diff --check`: exit 0 after removing trailing spaces on changed lines.
- Skill creator `quick_validate.py` under explicit Python UTF-8 mode: all ten skills exit 0. Initial default-encoding validation failed for the frontend skill with a Windows cp1252 decode error (exit 1); rerunning with `-X utf8` resolved it without changing the skill's original content encoding.
- Local Markdown link existence and exact filename-case audit: all 52 links passed before this report; the report's two additional local links were included in the final recheck.
- SQLite standard-library parse of the illustrative DDL: exit 0, five skeleton tables created in memory with FK enforcement; no WAL enabled. This validates example syntax only, not Alembic or application behavior.
- Preservation assertions: route lines and JSON/TypeScript/Python fenced examples unchanged in frontend-backend-contract, case-schema, hospital-api and agent-tools; tracked UI/data paths unchanged.
- Database/sidecar ignore probes: 5/5 passed. Repository legacy-term audit completed as classified above.

No application tests, runtime migrations, pnpm/uv application commands, Docker deployment or manual UI acceptance were run: their implementation/configuration does not exist. No application behavior is claimed verified.

Remaining specification work (not silently resolved):

1. `docs/evidence-contract.md` is missing. Finalize citation/anchor and evidence contract decisions before implementing that interface; README marks the gap instead of linking to a nonexistent document. Existing evidence schemas/examples were not replaced.
2. Existing examples differ on patient IDs (`PAT-001` versus `SYN-001`). P0-02 must record the canonical mapping rather than rename public identifiers during a storage migration.
3. State-machine/database examples propose `partial`, while the frontend contract uses `completed_with_limitations`; finding/tool vocabularies also need the existing P0-02 audit. Preserve contract values and approve explicit mappings before migrations or generated types encode these choices.
4. Manifests, exact toolchain pins, migrations, centralized settings, PRAGMA hooks, seed/reset scripts, Dockerfiles/services and test scripts are planned implementation work. The database path cannot be verified against nonexistent backend startup code; the shared policy defines the required resolution and acceptance tests.
5. The requested separate validation skill is absent. Validation guidance is maintained in the existing testing strategy, database skill, evaluation plan and shared stack policy; no extra skill was invented.

These issues block their affected interface work, not the approved stack decision. The narrow correction is to complete P0-02 contract decisions and the missing evidence contract, preserving existing routes and schemas until those decisions are explicit.

## F. Exact first coding task

Begin Phase 1 with the bounded P0-04 foundation bootstrap (after the P0-01 inventory; P0-02 remains prerequisite for affected domain schemas): create the Next.js App Router/pnpm manifest and lockfile and FastAPI/uv pyproject/lockfile, pin compatible toolchain versions, implement shared settings and absolute database-path resolution, the async SQLite connection/session lifespan and Alembic environment. Do not add clinical entities or agent behavior in this slice. Verify root/API path equivalence, explicit test-path overrides, WAL for file databases, FK/busy timeout on each new connection, session cleanup and engine shutdown using isolated temporary files. Establish configured development/test scripts without claiming availability before they exist. Then proceed through contract-resolved models, validated CASE-001 import and hospital retrieval toward the first genuine end-to-end investigation.
