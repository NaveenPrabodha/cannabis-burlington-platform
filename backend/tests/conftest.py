"""
Test fixtures.

Override the app's DB engine to use NullPool so each query opens a fresh
connection — avoids 'event loop is closed' errors when pytest-asyncio rotates
event loops between tests.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import database as db_mod
from app.config import get_settings


@pytest.fixture(autouse=True, scope="session")
def _swap_engine_to_nullpool():
    settings = get_settings()
    test_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    test_sessionmaker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    db_mod.engine = test_engine
    db_mod.AsyncSessionLocal = test_sessionmaker
    yield


@pytest.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
