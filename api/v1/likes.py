from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument

from core.settings import settings
from db.mongodb import get_database
from schemas.likes import (
    FilmRatingCreate,
    FilmRatingResponse,
    FilmRatingStats,
    LikedFilm,
)
from utils.auth import get_current_user
from utils.helpers import document_to_dict
from utils.rate_limit import limiter

router = APIRouter()

_col = settings.mongodb.collections


@router.get("/films/{film_id}/ratings/stats", response_model=FilmRatingStats)
@limiter.limit("60/minute")
async def get_film_rating_stats(
    request: Request,
    film_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    pipeline = [
        {"$match": {"film_id": film_id}},
        {
            "$group": {
                "_id": None,
                "total_ratings": {"$sum": 1},
                "average_rating": {"$avg": "$rating"},
                "likes_count": {"$sum": {"$cond": [{"$gte": ["$rating", 6]}, 1, 0]}},
                "dislikes_count": {"$sum": {"$cond": [{"$lte": ["$rating", 4]}, 1, 0]}},
                "neutral_count": {"$sum": {"$cond": [{"$eq": ["$rating", 5]}, 1, 0]}},
            }
        },
    ]
    result = await db[_col.film_ratings].aggregate(pipeline).to_list(1)
    if not result:
        return FilmRatingStats(
            film_id=film_id,
            total_ratings=0,
            likes_count=0,
            dislikes_count=0,
            neutral_count=0,
        )
    data = result[0]
    return FilmRatingStats(
        film_id=film_id,
        total_ratings=data["total_ratings"],
        likes_count=data["likes_count"],
        dislikes_count=data["dislikes_count"],
        neutral_count=data["neutral_count"],
        average_rating=round(data["average_rating"], 2),
    )


@router.post(
    "/films/{film_id}/ratings",
    response_model=FilmRatingResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_film_rating(
    film_id: str,
    body: FilmRatingCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    now = datetime.now(timezone.utc)
    doc = await db[_col.film_ratings].find_one_and_update(
        {"user_id": user_id, "film_id": film_id},
        {
            "$set": {"rating": body.rating, "updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return FilmRatingResponse(**document_to_dict(doc))


@router.delete("/films/{film_id}/ratings", status_code=status.HTTP_204_NO_CONTENT)
async def delete_film_rating(
    film_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    result = await db[_col.film_ratings].delete_one({"user_id": user_id, "film_id": film_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")


@router.get("/users/me/liked-films", response_model=List[LikedFilm])
async def get_liked_films(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    cursor = (
        db[_col.film_ratings]
        .find(
            {"user_id": user_id, "rating": {"$gte": 6}},
            {"film_id": 1, "rating": 1, "created_at": 1},
        )
        .sort("created_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [LikedFilm(**document_to_dict(doc)) for doc in docs]
