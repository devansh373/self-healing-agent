"""
Pytest configuration and shared async fixtures.

Provides:
  - Clean test database isolation (truncating tables before each test).
  - AsyncSession fixture wired to Postgres `selfheal_test`.
  - AsyncClient fixture overriding FastAPI's get_db dependency.
  - Patches AsyncSessionLocal so background tasks also run against selfheal_test.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.api.deployments as deployments_module
import app.core.db as db_module
from app.core.db import get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/selfheal_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Patch AsyncSessionLocal so background tasks triggered during tests use selfheal_test
db_module.AsyncSessionLocal = TestSessionLocal
deployments_module.AsyncSessionLocal = TestSessionLocal


@pytest_asyncio.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    """Truncate tables before each test to guarantee clean isolation."""
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE deployments, healing_attempts CASCADE;"))
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session connected to selfheal_test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Yield an AsyncClient with get_db overridden to use db_session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
