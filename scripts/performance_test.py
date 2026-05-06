"""
Performance tests for UGC service.

Usage:
    python -m scripts.performance_test
"""

import asyncio
import statistics
import time
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING

from core.settings import settings

ITERATIONS = 100


def _fmt(values: list[float]) -> str:
    ms = [v * 1000 for v in values]
    return (
        f"avg={statistics.mean(ms):.2f}ms  "
        f"min={min(ms):.2f}ms  "
        f"max={max(ms):.2f}ms  "
        f"p95={sorted(ms)[int(len(ms) * 0.95)]:.2f}ms"
    )


async def scenario_liked_films(db, user_id: str) -> list[float]:
    col = db[settings.mongodb.collections.film_ratings]
    times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        await col.find(
            {"user_id": user_id, "rating": {"$gte": 6}},
            {"film_id": 1, "rating": 1},
        ).to_list(length=200)
        times.append(time.perf_counter() - t0)
    return times


async def scenario_film_likes_count(db, film_id: str) -> list[float]:
    col = db[settings.mongodb.collections.film_ratings]
    pipeline = [
        {"$match": {"film_id": film_id}},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "avg": {"$avg": "$rating"},
                "likes": {"$sum": {"$cond": [{"$gte": ["$rating", 6]}, 1, 0]}},
                "dislikes": {"$sum": {"$cond": [{"$lte": ["$rating", 4]}, 1, 0]}},
            }
        },
    ]
    times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        await col.aggregate(pipeline).to_list(1)
        times.append(time.perf_counter() - t0)
    return times


async def scenario_bookmarks(db, user_id: str) -> list[float]:
    col = db[settings.mongodb.collections.bookmarks]
    times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        await col.find({"user_id": user_id}).sort("created_at", DESCENDING).to_list(length=200)
        times.append(time.perf_counter() - t0)
    return times


async def scenario_average_rating(db, film_id: str) -> list[float]:
    col = db[settings.mongodb.collections.film_ratings]
    pipeline = [
        {"$match": {"film_id": film_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}},
    ]
    times = []
    for _ in range(ITERATIONS):
        t0 = time.perf_counter()
        await col.aggregate(pipeline).to_list(1)
        times.append(time.perf_counter() - t0)
    return times


async def scenario_write_latency(db, user_id: str, film_id: str) -> dict:
    col = db[settings.mongodb.collections.film_ratings]
    write_times = []
    read_after_write_times = []

    for i in range(50):
        test_film = f"perf-test-film-{i}"
        now = datetime.now(timezone.utc)

        t0 = time.perf_counter()
        await col.update_one(
            {"user_id": user_id, "film_id": test_film},
            {"$set": {"rating": 8, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        write_times.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        doc = await col.find_one({"user_id": user_id, "film_id": test_film})
        read_after_write_times.append(time.perf_counter() - t0)

        assert doc is not None, "Written document not found immediately!"

    await col.delete_many({"film_id": {"$regex": "^perf-test-film-"}})
    return {"write": write_times, "read_after_write": read_after_write_times}


async def get_sample_ids(db) -> tuple[str, str]:
    rating = await db[settings.mongodb.collections.film_ratings].find_one({})
    if not rating:
        raise RuntimeError("No data found. Run `python -m scripts.generate_data` first.")
    return rating["user_id"], rating["film_id"]


async def main():
    client = AsyncIOMotorClient(settings.mongodb.url)
    db = client[settings.mongodb.db]

    print("Fetching sample IDs from DB...")
    user_id, film_id = await get_sample_ids(db)
    print(f"  user_id = {user_id}")
    print(f"  film_id = {film_id}")
    print(f"  iterations per scenario = {ITERATIONS}\n")

    print("=" * 65)
    print("READ SCENARIOS (pre-loaded data)")
    print("=" * 65)

    results = await asyncio.gather(
        scenario_liked_films(db, user_id),
        scenario_film_likes_count(db, film_id),
        scenario_bookmarks(db, user_id),
        scenario_average_rating(db, film_id),
    )

    labels = [
        "[1] Liked films list (rating >= 6)",
        "[2] Film likes/dislikes count + average rating",
        "[3] Bookmarks list",
        "[4] Average film rating",
    ]
    for label, times in zip(labels, results):
        print(f"\n{label}")
        print(f"    {_fmt(times)}")

    print("\n" + "=" * 65)
    print("WRITE + IMMEDIATE READ LATENCY (50 iterations)")
    print("=" * 65)

    result = await scenario_write_latency(db, user_id, film_id)
    print("\n[5] Add rating (upsert)")
    print(f"    write:            {_fmt(result['write'])}")
    print(f"    read after write: {_fmt(result['read_after_write'])}")

    client.close()
    print("\nPerformance test complete.")


if __name__ == "__main__":
    asyncio.run(main())
