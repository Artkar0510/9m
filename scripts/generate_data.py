"""
Generate test data for UGC service.

Usage:
    python -m scripts.generate_data
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Iterable

from bson import ObjectId
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import InsertOne, UpdateOne

sys.path.insert(0, ".")
from core.settings import settings

fake = Faker()

NUM_USERS = 10_000
NUM_FILMS = 1_000
RATINGS_PER_USER = 20
REVIEWS_PER_FILM = 50
BOOKMARKS_PER_USER = 10
BATCH_SIZE = 5_000


def random_past_datetime(days: int = 365) -> datetime:
    delta = timedelta(seconds=random.randint(0, days * 86400))
    return datetime.now(timezone.utc) - delta


async def _bulk_insert_batched(collection, docs: Iterable[dict], batch_size: int = BATCH_SIZE) -> int:
    ops = []
    count = 0
    for doc in docs:
        ops.append(InsertOne(doc))
        count += 1
        if len(ops) >= batch_size:
            await collection.bulk_write(ops, ordered=False)
            ops.clear()
    if ops:
        await collection.bulk_write(ops, ordered=False)
    return count


def _rating_docs(user_ids: list, film_ids: list):
    seen = set()
    for user_id in user_ids:
        for film_id in random.sample(film_ids, min(RATINGS_PER_USER, len(film_ids))):
            if (user_id, film_id) in seen:
                continue
            seen.add((user_id, film_id))
            now = random_past_datetime()
            yield {"user_id": user_id, "film_id": film_id, "rating": random.randint(0, 10),
                   "created_at": now, "updated_at": now}


def _bookmark_docs(user_ids: list, film_ids: list):
    seen = set()
    for user_id in user_ids:
        for film_id in random.sample(film_ids, min(BOOKMARKS_PER_USER, len(film_ids))):
            if (user_id, film_id) in seen:
                continue
            seen.add((user_id, film_id))
            yield {"user_id": user_id, "film_id": film_id, "created_at": random_past_datetime()}


async def generate_film_ratings(db, user_ids: list, film_ids: list) -> int:
    col = settings.mongodb.collections
    total = await _bulk_insert_batched(db[col.film_ratings], _rating_docs(user_ids, film_ids))
    print(f"  film_ratings: {total:,} documents")
    return total


async def generate_reviews(db, user_ids: list, film_ids: list) -> list[str]:
    col = settings.mongodb.collections
    collection = db[col.reviews]
    ops = []
    review_ids = []

    for film_id in film_ids:
        for user_id in random.sample(user_ids, min(REVIEWS_PER_FILM, len(user_ids))):
            oid = ObjectId()
            review_ids.append(str(oid))
            ops.append(InsertOne({
                "_id": oid,
                "user_id": user_id,
                "film_id": film_id,
                "author": fake.user_name(),
                "text": fake.paragraph(nb_sentences=random.randint(2, 6)),
                "film_rating": random.choice([None, random.randint(0, 10)]),
                "published_at": random_past_datetime(),
                "likes_count": 0,
                "dislikes_count": 0,
            }))
            if len(ops) >= BATCH_SIZE:
                await collection.bulk_write(ops, ordered=False)
                ops.clear()

    if ops:
        await collection.bulk_write(ops, ordered=False)

    print(f"  reviews: {len(review_ids):,} documents")
    return review_ids


async def generate_review_likes(db, user_ids: list, review_ids: list) -> int:
    col = settings.mongodb.collections
    collection = db[col.review_likes]
    reviews_col = db[col.reviews]
    seen = set()
    ops = []

    for review_id in random.sample(review_ids, min(10_000, len(review_ids))):
        for user_id in random.sample(user_ids, random.randint(0, 30)):
            if (user_id, review_id) in seen:
                continue
            seen.add((user_id, review_id))
            ops.append(InsertOne({
                "review_id": review_id,
                "user_id": user_id,
                "is_like": random.random() > 0.3,
                "created_at": random_past_datetime(),
            }))
            if len(ops) >= BATCH_SIZE:
                await collection.bulk_write(ops, ordered=False)
                ops.clear()

    if ops:
        await collection.bulk_write(ops, ordered=False)

    pipeline = [
        {"$group": {
            "_id": "$review_id",
            "likes": {"$sum": {"$cond": ["$is_like", 1, 0]}},
            "dislikes": {"$sum": {"$cond": ["$is_like", 0, 1]}},
        }},
    ]
    update_ops = []
    async for stat in collection.aggregate(pipeline):
        try:
            update_ops.append(UpdateOne(
                {"_id": ObjectId(stat["_id"])},
                {"$set": {"likes_count": stat["likes"], "dislikes_count": stat["dislikes"]}},
            ))
        except Exception:
            pass
    if update_ops:
        await reviews_col.bulk_write(update_ops, ordered=False)

    total = await collection.count_documents({})
    print(f"  review_likes: {total:,} documents")
    return total


async def generate_bookmarks(db, user_ids: list, film_ids: list) -> int:
    col = settings.mongodb.collections
    total = await _bulk_insert_batched(db[col.bookmarks], _bookmark_docs(user_ids, film_ids))
    print(f"  bookmarks: {total:,} documents")
    return total


async def main():
    client = AsyncIOMotorClient(settings.mongodb.url)
    db = client[settings.mongodb.db]

    print("Dropping existing data...")
    col = settings.mongodb.collections
    for name in [col.film_ratings, col.reviews, col.review_likes, col.bookmarks]:
        await db[name].drop()

    from db.mongodb import _create_indexes
    await _create_indexes(db)

    print(f"Generating {NUM_USERS:,} users and {NUM_FILMS:,} films...")
    user_ids = [str(fake.uuid4()) for _ in range(NUM_USERS)]
    film_ids = [str(fake.uuid4()) for _ in range(NUM_FILMS)]

    print("Inserting data:")
    review_ids, _ = await asyncio.gather(
        generate_reviews(db, user_ids, film_ids),
        generate_film_ratings(db, user_ids, film_ids),
    )
    await asyncio.gather(
        generate_review_likes(db, user_ids, review_ids),
        generate_bookmarks(db, user_ids, film_ids),
    )

    print(f"\nDone. sample_user_id={user_ids[0]!r}  sample_film_id={film_ids[0]!r}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
