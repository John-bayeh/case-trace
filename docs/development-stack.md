# CASETRACE — Development stack and SQLite operations

Status: approved stack and operational policy. Phase 1 manifests, lockfiles, baseline migration, commands and Dockerfiles now exist. See [local development](local-development.md) for setup and [Phase 1 report](phase-1-report.md) for executed validation. Domain, worker, seeding and recovery requirements below remain future implementation obligations.

## Stack and toolchain

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui; pnpm and `apps/web/pnpm-lock.yaml`.
- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.x asyncio, Alembic, uv; `apps/api/pyproject.toml` and `apps/api/uv.lock`.
- MVP storage: SQLite through `sqlite+aiosqlite`; local database `data/runtime/casetrace.db`. Assets remain in `data/assets/` and existing case asset locations, outside database blobs.
- Planned execution: controlled agent orchestration, asyncio workers and SSE. These are not implemented by the Phase 1 foundation. No additional infrastructure is required.

The foundation pins Node.js 24.22.0 in `.node-version`, pnpm 10.34.0 in `packageManager`, and Python 3.12 in `apps/api/.python-version`. The web manifest declares Node 24 support. uv 0.11.17 is used for validation and pinned in the API Dockerfile. Lockfiles select exact dependencies. Next.js supports Node 20.9 and above; Node 24 satisfies that requirement. No CI pipeline is installed yet; future CI must use these pins and locked installs.

## Development commands

Run frontend commands from `apps/web`:

```sh
pnpm install
pnpm dev
pnpm build
pnpm lint
pnpm test
```

These scripts are defined: ESLint runs directly, `test` runs Vitest, and `typecheck` runs TypeScript. One web application does not require a pnpm workspace. Preserve `pnpm-lock.yaml`; CI should use `pnpm install --frozen-lockfile` with the pinned pnpm version.

Run backend commands from `apps/api`:

```sh
uv python pin 3.12
uv sync
uv add <package>
uv add --dev <package>
uv lock
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
uv run alembic upgrade head
uv run pytest
```

`pyproject.toml` owns dependency declarations; commit `uv.lock`. uv manages `apps/api/.venv`; manual activation is unnecessary. Add only dependencies needed by the implementation task. In CI use `uv sync --locked` and `uv run --locked pytest` so stale lockfiles fail rather than being updated. Add tooling such as Ruff only when configured, then invoke it through `uv run`. Stop local servers with Ctrl+C. See the [demo runbook](demo-runbook.md) for planned validation, seed and reset commands.

## Central configuration and paths

Phase 1 provides one settings loader shared by API, Alembic and tests; future workers and seeds must reuse it. It loads the root `.env` explicitly rather than depending on process working directory; process environment and explicit test overrides take precedence.

`CASETRACE_ROOT` optionally supplies an absolute repository/data root. Otherwise derive the root from the installed source location of `apps/api/app/core/config.py` (four parents above that file's containing directory), never `Path.cwd()`. Validate that configured roots are absolute and expected directories exist. If packaging changes that layout, require `CASETRACE_ROOT` rather than guessing.

Default input:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/runtime/casetrace.db
SQLITE_BUSY_TIMEOUT_MS=5000
ASSET_STORAGE_PATH=./data/assets
```

Parse URLs using SQLAlchemy URL utilities. Resolve relative SQLite database filenames and asset paths against `CASETRACE_ROOT`, then construct an absolute SQLAlchemy URL; preserve explicit absolute test paths and the `:memory:` sentinel. Reject unsupported URL schemes/configuration instead of silently choosing a different database. Create the database parent directory before connecting, including in Alembic and seeds. Never rewrite test paths to the demo database. Verify root and `apps/api` invocations resolve to the same file.

Docker is optional; local development is preferred. Compose defines only `api` and `web`, sets `CASETRACE_ROOT=/app`, maps host `./data/runtime` to writable `/app/data/runtime`, and mounts assets read-only. The API runs migrations before serving. Cases and evaluator keys are excluded. Use one API process; future workers remain in process with no replicas sharing the writable database. Keep WAL storage on a local filesystem, not a network share. Commands are `docker compose up --build` and `docker compose down`; stopping retains runtime storage. Do not use volume removal as a reset shortcut. Container execution still requires independent Docker validation; see the Phase 1 report.

## Connection lifecycle and transaction policy

Create one async engine per application lifespan and an `async_sessionmaker`; dispose the engine at shutdown. Give each request or persistence operation its own `AsyncSession` using an async context manager. Never share sessions between concurrent agent tasks. Roll back on failure and close sessions on every path. Materialize typed results before leaving a read operation; no live ORM sessions in agent context or SSE streams.

At controlled initialization, outside a transaction, set and verify `PRAGMA journal_mode=WAL` for file databases. On **every** connection, including migration/seed/test connections, configure `PRAGMA foreign_keys=ON` outside an active transaction and `PRAGMA busy_timeout=5000` (or the validated configured milliseconds). Test the actual driver transaction-control hooks; SQLite driver defaults can otherwise undermine DDL rollback and savepoints. For aiosqlite, SQLAlchemy connection hooks attach to the async engine's `sync_engine`. WAL persists on the file but foreign-key enforcement and busy timeout are connection settings. Do not enable WAL for in-memory tests.

WAL supports concurrent readers and a writer; SQLite still permits only one writer at a time. Route investigation mutations through one application persistence service with short explicit transactions. Within one process, serialize write critical sections with a bounded asyncio lock; uniqueness constraints and compare-and-swap guards remain authoritative. Do not use row locks or `SELECT FOR UPDATE`. Close read transactions promptly too, to avoid retaining WAL snapshots.

Separate each tool/agent operation into short audit-start commit, session-free external work, and short audit-result/state commit. Never keep a transaction open during LLM inference, network/tool waits, asset generation, or SSE delivery. Repository reads inside a clinical tool get their own bounded session. Retry only a whole rolled-back idempotent persistence operation for transient lock contention, with a bounded attempt/time budget; report exhausted contention explicitly. Never rerun model calls as an implicit database retry.

State updates use `UPDATE ... WHERE id=:id AND version=:expected_version AND status=:expected_status`, increment version, and require exactly one affected row. A stale result must be reloaded and reconciled or rejected, never overwrite newer state. Allocate the next event sequence and commit state, evidence/finding links and the durable event atomically where they form one transition. Stream only committed events. Use existing idempotency keys, attempt IDs and unique logical result keys to prevent duplicate findings on retries. Recover interrupted runs from persisted state under the state machine's bounded recovery policy; do not silently mark them complete.

## Storage, migrations and isolation

Preserve every entity and relationship in the [database schema](database-schema.md). Hospital and investigation are logical service/module boundaries in one SQLite database, not PostgreSQL schemas. SQLite has no per-table users or grants: enforce clinical immutability in repository APIs, patient scope in services, and file permissions at the OS/container boundary. Ground truth stays in physically separate evaluator-only files/processes that are unavailable to runtime. A read-only repository convention alone cannot isolate an answer key stored in the same runtime file.

Use application-generated UUIDs with SQLAlchemy `Uuid(as_uuid=True)` (portable emulation on SQLite); keep public source identifiers unchanged. Use SQLAlchemy `JSON`, backed by text on SQLite, for structured metadata; index normal scalar columns for important filters. Avoid reliance on JSONB operators or database enum types. Use validated string enums plus named check constraints after contract conflicts are resolved. Do not change existing public enum values as part of this migration.

Known instants enter as timezone-aware values normalized to UTC. A shared SQLAlchemy type adapter must reject naive inputs, store UTC using SQLite-compatible `DateTime` serialization, and restore UTC awareness on load; `DateTime(timezone=True)` alone does not preserve SQLite offsets. Preserve original literal/offset, precision, and each clinical time field separately. Date-only source values remain dates, never invented midnight instants. SQLAlchemy/native types can later map to PostgreSQL UUID, JSONB and timezone-aware timestamps without changing public IDs or timestamp semantics.

Use Alembic revisions for persistent databases, not `create_all()`. The Alembic async environment uses the shared settings/connection factory and `run_sync`; review autogenerated migrations, use batch table recreation for unsupported ALTER operations, preserve named constraints/indexes, back up before destructive changes, and run foreign-key checks after migration. Never rewrite applied revisions. Revision `0001_foundation` establishes version tracking only; domain tables await P0-02. SQLite JSON features depend on the linked library; test required operators. Database schema changes and concurrent seeds require exclusive maintenance, not a live agent run.

Use a unique temporary file database per test/parallel worker and the same connection configuration as production. File-backed integration tests cover WAL, lock contention, migrations and recovery. In-memory unit databases skip WAL and need an explicit shared connection/pool policy if accessed through several sessions; otherwise each connection may see a different database. Test root/path overrides, FK checks on newly opened connections, UTC round trips, version conflicts, idempotent findings, rollback and no answer-key leakage. Never point tests at `data/runtime/casetrace.db`.

## Backup, recovery and future database migration

Use SQLite's online backup API for a consistent live snapshot; run blocking backup work outside the async request loop. Do not copy only a live `.db` file and discard its WAL. Alternatively stop all users, checkpoint successfully, close connections, then copy the quiescent file. Record migration revision, dataset version/checksum and matching asset manifest with the backup. Store backups outside version control.

For recovery stop all processes, archive the failed database and associated sidecars together, restore a verified snapshot to the configured absolute path, check `PRAGMA integrity_check` and `PRAGMA foreign_key_check`, verify Alembic revision and asset hashes, then restart and reconcile interrupted runs. Do not delete a live WAL/SHM file. Reconstruct source records from frozen canonical fixtures and migrations/seeds when no backup exists; lost runtime investigations cannot be reconstructed from fixtures alone.

A future PostgreSQL move is a separate reviewed migration: add the driver, map portable types, export/import and verify counts, IDs, UTC instants and evidence hashes, rerun migrations/integration/concurrency tests, then change deployment configuration. Revisit row locking, credentials and multiple workers only then. No PostgreSQL service or driver is needed for this MVP.

## Technical references

- [Node.js release lifecycle](https://nodejs.org/en/about/previous-releases) and [pnpm compatibility](https://pnpm.io/installation).
- [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).
- [SQLAlchemy SQLite dialect and transaction control](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).
- [SQLite WAL and its single-writer constraint](https://www.sqlite.org/wal.html), [connection PRAGMAs](https://www.sqlite.org/pragma.html), and [backup API](https://www.sqlite.org/backup.html).
- [Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html).
