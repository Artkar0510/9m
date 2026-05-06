import asyncio

import httpx
import pytest_asyncio
from contextlib import asynccontextmanager
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.settings import settings
from db.mongodb import _create_indexes, get_client, get_database
from main import app
from utils.auth import UserInfo, get_current_user, get_current_user_info

TEST_USER_ID = "test-user-550e8400-e29b-41d4"


# Skip connect_to_mongo() in tests — the test_db fixture provides the Motor client.
@asynccontextmanager
async def _test_lifespan(app):
    app.state.http_client = httpx.AsyncClient()
    app.state.redis = None  # cache bypassed in tests; get_current_user_info is overridden anyway
    yield
    await app.state.http_client.aclose()


app.router.lifespan_context = _test_lifespan


_rs_ready = False


async def _ensure_replica_set(client: AsyncIOMotorClient) -> None:
    global _rs_ready
    if _rs_ready:
        return
    try:
        await client.admin.command("replSetGetStatus")
    except Exception:
        await client.admin.command("replSetInitiate")
        for _ in range(30):
            await asyncio.sleep(0.5)
            try:
                status = await client.admin.command("replSetGetStatus")
                if any(m.get("stateStr") == "PRIMARY" for m in status.get("members", [])):
                    break
            except Exception:
                pass
    _rs_ready = True


@pytest_asyncio.fixture
async def mongo_client():
    # directConnection=True bypasses RS member-hostname discovery: the driver
    # connects to exactly the host in the URL instead of redirecting to the
    # RS-advertised member address (which is an internal Docker hostname when
    # running via docker-compose port mapping).
    client = AsyncIOMotorClient(settings.mongodb.url, directConnection=True)
    await _ensure_replica_set(client)
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
async def client(mongo_client, test_db) -> AsyncClient:
    async def override_db():
        return test_db

    async def override_client():
        return mongo_client

    async def override_auth():
        return TEST_USER_ID

    async def override_auth_info():
        return UserInfo(user_id=TEST_USER_ID, username="TestUser")

    app.dependency_overrides[get_database] = override_db
    app.dependency_overrides[get_client] = override_client
    app.dependency_overrides[get_current_user] = override_auth
    app.dependency_overrides[get_current_user_info] = override_auth_info

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
