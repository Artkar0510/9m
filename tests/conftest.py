import httpx
import pytest_asyncio
from contextlib import asynccontextmanager
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.settings import settings
from db.mongodb import _create_indexes, get_database
from main import app
from utils.auth import get_current_user

TEST_USER_ID = "test-user-550e8400-e29b-41d4"


# Skip connect_to_mongo() in tests — the test_db fixture provides the Motor client.
@asynccontextmanager
async def _test_lifespan(app):
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app.router.lifespan_context = _test_lifespan


@pytest_asyncio.fixture
async def mongo_client():
    client = AsyncIOMotorClient(settings.mongodb.url)
    yield client
    client.close()


@pytest_asyncio.fixture
async def test_db(mongo_client) -> AsyncIOMotorDatabase:
    db = mongo_client[settings.mongodb.test_db]
    await _create_indexes(db)
    col = settings.mongodb.collections
    for name in [col.film_ratings, col.reviews, col.review_likes, col.bookmarks]:
        await db[name].delete_many({})
    return db


@pytest_asyncio.fixture
async def client(test_db) -> AsyncClient:
    async def override_db():
        return test_db

    async def override_auth():
        return TEST_USER_ID

    app.dependency_overrides[get_database] = override_db
    app.dependency_overrides[get_current_user] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
