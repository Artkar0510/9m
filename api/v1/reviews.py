from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from core.settings import settings
from db.mongodb import get_database
from schemas.reviews import (
    ReviewCreate,
    ReviewLikeCreate,
    ReviewLikeResponse,
    ReviewResponse,
    SortBy,
    SortOrder,
)
from utils.auth import get_current_user
from utils.helpers import document_to_dict, require_object_id

router = APIRouter()

_col = settings.mongodb.collections


@router.get("/films/{film_id}/reviews", response_model=List[ReviewResponse])
async def get_film_reviews(
    film_id: str,
    sort_by: SortBy = Query(SortBy.published_at),
    order: SortOrder = Query(SortOrder.desc),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    sort_direction = DESCENDING if order == SortOrder.desc else ASCENDING
    cursor = (
        db[_col.reviews]
        .find({"film_id": film_id})
        .sort(sort_by.value, sort_direction)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [ReviewResponse(**document_to_dict(doc)) for doc in docs]


@router.post(
    "/films/{film_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    film_id: str,
    body: ReviewCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "film_id": film_id,
        "author": body.author,
        "text": body.text,
        "film_rating": body.film_rating,
        "published_at": now,
        "likes_count": 0,
        "dislikes_count": 0,
    }
    result = await db[_col.reviews].insert_one(doc)
    doc["_id"] = result.inserted_id
    return ReviewResponse(**document_to_dict(doc))


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    oid = require_object_id(review_id, "review_id")
    doc = await db[_col.reviews].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return ReviewResponse(**document_to_dict(doc))


@router.post("/reviews/{review_id}/likes", response_model=ReviewLikeResponse)
async def upsert_review_like(
    review_id: str,
    body: ReviewLikeCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    oid = require_object_id(review_id, "review_id")

    if not await db[_col.reviews].find_one({"_id": oid}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    now = datetime.now(timezone.utc)
    existing = await db[_col.review_likes].find_one({"user_id": user_id, "review_id": review_id})

    if existing:
        if existing["is_like"] == body.is_like:
            return ReviewLikeResponse(**document_to_dict(existing))
        inc = {"likes_count": 1, "dislikes_count": -1} if body.is_like else {"likes_count": -1, "dislikes_count": 1}
        updated = await db[_col.review_likes].find_one_and_update(
            {"_id": existing["_id"]},
            {"$set": {"is_like": body.is_like}},
            return_document=ReturnDocument.AFTER,
        )
        await db[_col.reviews].update_one({"_id": oid}, {"$inc": inc})
        return ReviewLikeResponse(**document_to_dict(updated))

    like_doc = {"review_id": review_id, "user_id": user_id, "is_like": body.is_like, "created_at": now}
    result = await db[_col.review_likes].insert_one(like_doc)
    like_doc["_id"] = result.inserted_id
    inc_field = "likes_count" if body.is_like else "dislikes_count"
    await db[_col.reviews].update_one({"_id": oid}, {"$inc": {inc_field: 1}})
    return ReviewLikeResponse(**document_to_dict(like_doc))


@router.delete("/reviews/{review_id}/likes", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review_like(
    review_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    oid = require_object_id(review_id, "review_id")
    existing = await db[_col.review_likes].find_one({"user_id": user_id, "review_id": review_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")

    await db[_col.review_likes].delete_one({"_id": existing["_id"]})
    dec_field = "likes_count" if existing["is_like"] else "dislikes_count"
    await db[_col.reviews].update_one({"_id": oid}, {"$inc": {dec_field: -1}})
