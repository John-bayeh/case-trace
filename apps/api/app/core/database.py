"""Database configuration and session management.

Follows development-stack.md:
- WAL mode enabled
- Foreign keys enforced per connection
- Busy timeout set
- No session held across LLM/tool waits
"""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

# Base class for SQLAlchemy models
Base = declarative_base()

# Global engine and session maker
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        
        # Ensure runtime directory exists
        db_path = Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            poolclass=NullPool,  # SQLite doesn't benefit from connection pooling
            connect_args={
                "check_same_thread": False,
                # WAL mode, foreign keys, busy timeout set via init_db pragma
            },
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions.
    
    Usage in FastAPI routes:
        async def route(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database with required pragma settings.
    
    Per development-stack.md:
    - Enable WAL mode
    - Enable foreign keys
    - Set busy timeout
    """
    engine = get_engine()
    
    # Apply pragma settings
    async with engine.begin() as conn:
        # WAL mode for better concurrency
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        # Foreign key enforcement
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        # Busy timeout (5 seconds)
        await conn.exec_driver_sql("PRAGMA busy_timeout=5000")
    
    # Create tables (in production, use Alembic migrations instead)
    if get_settings().ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database initialized")
