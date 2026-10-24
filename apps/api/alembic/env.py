import asyncio

from alembic import context
from app.core.config import load_settings
from app.core.database import Database
from app.models.base import Base


def run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online():
    database = Database(load_settings())
    try:
        await database.initialize()
        async with database.engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await database.dispose()


if context.is_offline_mode():
    context.configure(
        url=load_settings().resolved_database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online())
