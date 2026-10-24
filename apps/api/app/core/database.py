"""One engine per lifespan, one short session per operation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.url = settings.resolved_database_url
        self.is_memory = self.url.database == ":memory:"
        if not self.is_memory:
            Path(str(self.url.database)).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_async_engine(
            self.url, **({"poolclass": StaticPool} if self.is_memory else {})
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

        @event.listens_for(self.engine.sync_engine, "connect")
        def configure_connection(connection: Any, _: Any) -> None:
            # Disable legacy driver BEGIN behavior: SQLAlchemy owns transactions,
            # including DDL and savepoints. PRAGMAs run before any BEGIN.
            connection.isolation_level = None
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
            finally:
                cursor.close()

        @event.listens_for(self.engine.sync_engine, "begin")
        def begin(connection: Connection) -> None:
            connection.exec_driver_sql("BEGIN")

    async def initialize(self) -> None:
        if not self.is_memory:
            # Raw driver access avoids SQLAlchemy's BEGIN hook for journal setup.
            async with self.engine.connect() as connection:
                raw = await connection.get_raw_connection()
                driver = raw.driver_connection
                assert driver is not None
                cursor = await driver.execute("PRAGMA journal_mode=WAL")
                try:
                    row = await cursor.fetchone()
                    if row is None or row[0].lower() != "wal":
                        raise RuntimeError("SQLite WAL initialization failed")
                finally:
                    await cursor.close()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessions() as session:
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()
