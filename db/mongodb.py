from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from core.settings import settings

_db_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo() -> None:
    global _db_client
    _db_client = AsyncIOMotorClient(settings.mongodb.url)
    await _create_indexes(_db_client[settings.mongodb.db])


async def close_mongo_connection() -> None:
    if _db_client:
        _db_client.close()


async def get_client() -> AsyncIOMotorClient:
    return _db_client


async def get_database() -> AsyncIOMotorDatabase:
    return _db_client[settings.mongodb.db]


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    col = settings.mongodb.collections

    await db[col.film_ratings].create_indexes([
        IndexModel(
            [("user_id", ASCENDING), ("film_id", ASCENDING)],
            unique=True,
            name="user_film_unique",
        ),
        IndexModel([("film_id", ASCENDING)], name="film_id_idx"),
        IndexModel([("user_id", ASCENDING)], name="user_id_idx"),
        IndexModel([("rating", ASCENDING)], name="rating_idx"),
    ])

    await db[col.reviews].create_indexes([
        IndexModel([("film_id", ASCENDING)], name="film_id_idx"),
        IndexModel([("user_id", ASCENDING)], name="user_id_idx"),
        IndexModel([("published_at", DESCENDING)], name="published_at_idx"),
        IndexModel([("likes_count", DESCENDING)], name="likes_count_idx"),
    ])

    await db[col.review_likes].create_indexes([
        IndexModel(
            [("user_id", ASCENDING), ("review_id", ASCENDING)],
            unique=True,
            name="user_review_unique",
        ),
        IndexModel([("review_id", ASCENDING)], name="review_id_idx"),
    ])

    await db[col.bookmarks].create_indexes([
        IndexModel(
            [("user_id", ASCENDING), ("film_id", ASCENDING)],
            unique=True,
            name="user_film_unique",
        ),
        IndexModel([("user_id", ASCENDING)], name="user_id_idx"),
        IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
    ])
