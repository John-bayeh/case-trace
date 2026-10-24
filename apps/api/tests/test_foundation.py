import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, load_settings
from app.core.database import Database
from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'isolated.db'}",
        sqlite_busy_timeout_ms=1234,
    )


def test_health_startup_errors_and_cors(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "1.0.0", "database": "connected"}
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["x-request-id"].startswith("req_")
        unknown = client.get("/api/patients")
        assert unknown.status_code == 404
        assert set(unknown.json()["error"]) == {"code", "message", "request_id"}
        assert (
            "access-control-allow-origin"
            not in client.get(
                "/api/health", headers={"Origin": "https://untrusted.example"}
            ).headers
        )


def test_path_independence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CASETRACE_ROOT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    expected = load_settings().resolved_database_url
    monkeypatch.chdir(ROOT / "apps" / "api")
    assert load_settings().resolved_database_url == expected
    monkeypatch.chdir(tmp_path)
    assert load_settings().resolved_database_url == expected
    assert Path(str(expected.database)) == ROOT / "data" / "runtime" / "casetrace.db"


def test_root_env_and_override_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "apps" / "api").mkdir(parents=True)
    (tmp_path / ".env").write_text("API_PORT=8123\nSQLITE_BUSY_TIMEOUT_MS=321\n")
    monkeypatch.setenv("CASETRACE_ROOT", str(tmp_path))
    monkeypatch.delenv("API_PORT", raising=False)
    assert load_settings().api_port == 8123
    monkeypatch.setenv("API_PORT", "8124")
    assert load_settings().api_port == 8124
    assert load_settings(api_port=8125).api_port == 8125
    assert load_settings().sqlite_busy_timeout_ms == 321


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/test",
        "sqlite:///foo",
        "sqlite+aiosqlite:///",
        "sqlite+aiosqlite:///file:test?uri=true",
    ],
)
def test_reject_unsupported_database(url: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        Settings(database_url=url)


def test_reject_invalid_settings() -> None:
    with pytest.raises(ValidationError):
        Settings(casetrace_root=Path("relative"))
    with pytest.raises(ValidationError):
        Settings(sqlite_busy_timeout_ms=-1)
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins=["*"])


async def test_database_pragmas_sessions_and_rollback(settings: Settings) -> None:
    database = Database(settings)
    try:
        await database.initialize()
        # Simultaneous checked-out connections verify connection-specific settings.
        async with database.engine.connect() as first, database.engine.connect() as second:
            for connection in (first, second):
                assert (await connection.execute(text("PRAGMA foreign_keys"))).scalar() == 1
                assert (await connection.execute(text("PRAGMA busy_timeout"))).scalar() == 1234
                assert (await connection.execute(text("PRAGMA journal_mode"))).scalar() == "wal"
        async with database.engine.begin() as connection:
            await connection.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
            await connection.execute(
                text(
                    "CREATE TABLE child (id INTEGER PRIMARY KEY, "
                    "parent_id INTEGER REFERENCES parent(id))"
                )
            )
        with pytest.raises(IntegrityError):
            async with database.session() as session, session.begin():
                await session.execute(text("INSERT INTO child VALUES (1, 99)"))
        with pytest.raises(RuntimeError):
            async with database.session() as session, session.begin():
                await session.execute(text("INSERT INTO parent VALUES (1)"))
                raise RuntimeError("force rollback")
        async with database.session() as session:
            assert (await session.execute(text("SELECT count(*) FROM parent"))).scalar() == 0
        with pytest.raises(RuntimeError):
            async with database.engine.begin() as connection:
                await connection.execute(text("CREATE TABLE rolled_back (id INTEGER)"))
                raise RuntimeError("DDL must roll back")
        async with database.engine.connect() as connection:
            assert (
                await connection.execute(
                    text("SELECT name FROM sqlite_master WHERE name='rolled_back'")
                )
            ).first() is None
        async with database.session() as session, session.begin():
            await session.execute(text("INSERT INTO parent VALUES (2)"))
            with pytest.raises(RuntimeError):
                async with session.begin_nested():
                    await session.execute(text("INSERT INTO parent VALUES (3)"))
                    raise RuntimeError("savepoint rollback")
        async with database.session() as session:
            assert (await session.execute(text("SELECT id FROM parent"))).scalars().all() == [2]
    finally:
        await database.dispose()
    assert database.engine.sync_engine.pool.checkedout() == 0


async def test_memory_skips_wal() -> None:
    database = Database(Settings(database_url="sqlite+aiosqlite:///:memory:"))
    try:
        await database.initialize()
        async with database.session() as session:
            assert (await session.execute(text("PRAGMA journal_mode"))).scalar() == "memory"
            assert (await session.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    finally:
        await database.dispose()


def test_alembic_upgrade_downgrade_and_cwd(settings: Settings) -> None:
    env = {**os.environ, "DATABASE_URL": str(settings.resolved_database_url)}
    config = str(ROOT / "apps" / "api" / "alembic.ini")
    for cwd, command in [
        (ROOT, ["upgrade", "head"]),
        (ROOT / "apps" / "api", ["current"]),
        (ROOT, ["downgrade", "base"]),
        (ROOT, ["upgrade", "head"]),
        (ROOT, ["check"]),
    ]:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", config, *command],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        if command == ["current"]:
            assert "0004_investigation" in result.stdout


def test_failed_database_health(settings: Settings) -> None:
    from app.api.dependencies import get_session

    class BrokenSession:
        async def execute(self, statement: object) -> None:
            from sqlalchemy.exc import OperationalError

            raise OperationalError("private connection details", {}, Exception("secret"))

    application = create_app(settings)
    application.dependency_overrides[get_session] = lambda: BrokenSession()
    with TestClient(application) as client:
        response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert "secret" not in response.text


def test_unexpected_error_and_validation_are_safe(settings: Settings) -> None:
    application = create_app(settings)

    @application.get("/test/failure")
    async def failure() -> None:
        raise RuntimeError("private secret")

    @application.get("/test/validation")
    async def validation(count: int) -> dict[str, int]:
        return {"count": count}

    with TestClient(application) as client:
        response = client.get("/test/failure", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 500
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert response.headers["x-request-id"] == response.json()["error"]["request_id"]
        assert "private secret" not in response.text
        response = client.get("/test/validation?count=invalid")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
