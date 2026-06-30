"""
Database engine and session factory.

Creates the async SQLAlchemy engine and provides a FastAPI dependency
that yields one database session per request, closing it afterwards.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────
# The engine is the starting point for all SQLAlchemy database operations.
# It maintains a connection pool internally — you never open raw connections yourself.
#
# echo=False  → don't log every SQL statement (too noisy for normal use)
# pool_size=5 → keep 5 connections open in the pool (default, fine for Phase 1)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# ── Session Factory ───────────────────────────────────────────────────────
# A "session" is a workspace for talking to the database: you load objects,
# modify them, and commit changes — all through the session.
#
# async_sessionmaker creates a factory: every time you call AsyncSessionLocal(),
# you get a NEW session. Each request gets its own session so they don't
# interfere with each other.
#
# expire_on_commit=False → after committing, you can still read attributes from
# ORM objects without triggering another database query. Without this, accessing
# e.g. deployment.status after commit would raise an error in async code.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────
# All ORM model classes inherit from this. It gives them the ability to be
# mapped to database tables. Alembic also reads Base.metadata to know
# what tables/columns should exist.
class Base(DeclarativeBase):
    pass


# ── FastAPI Dependency ────────────────────────────────────────────────────
# This is a "dependency" — a function FastAPI calls automatically when a route
# needs a database session. The route declares it needs one:
#
#   async def my_route(db: AsyncSession = Depends(get_db)):
#
# FastAPI calls get_db(), which:
#   1. Creates a new session
#   2. Yields it to the route function
#   3. After the route returns (or raises), closes the session in the finally block
#
# This pattern guarantees sessions are always cleaned up, even if an error occurs.
async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
