"""
Alembic env.py — configured for async SQLAlchemy.

This file is the bridge between Alembic (migration tool) and our database.
Alembic reads this to know:
  1. How to connect to the database (via DATABASE_URL env var)
  2. What the "desired" schema looks like (via Base.metadata from our ORM models)

The key challenge: Alembic was originally built for synchronous database access,
but we use an async driver (asyncpg). The solution is to:
  - Create an async engine
  - Run the migration inside an async function
  - Use connection.run_sync() to bridge async → sync for the actual DDL execution
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# ── Import all models so Base.metadata knows about them ──────────────────
# This import looks unused but is CRITICAL: without it, Base.metadata has no
# tables registered and --autogenerate would produce an empty migration.
from app.models.deployment import Base  # noqa: F401

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set up Python logging from the .ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what Alembic compares against the actual database to figure out
# what's changed (new tables, new columns, etc.)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without connecting to the DB.

    Useful for generating SQL scripts to run manually (e.g., in environments
    where you can't connect directly to production).
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run the actual migration operations against a live connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create an async engine, then run migrations synchronously through it.

    This is the standard async Alembic pattern:
    1. Create an async engine from our DATABASE_URL
    2. Get a connection from it
    3. Use connection.run_sync() to run the synchronous migration code
       inside the async context
    """
    connectable = create_async_engine(settings.DATABASE_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the real database.

    This is what runs when you execute `alembic upgrade head`.
    """
    asyncio.run(run_async_migrations())


# Alembic calls one of these based on whether --sql flag was used
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
