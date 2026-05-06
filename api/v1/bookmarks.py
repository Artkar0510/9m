from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from core.settings import settings
from db.mongodb import get_database
from schemas.bookmarks import BookmarkCreate, BookmarkResponse
from utils.auth import get_current_user
from utils.helpers import document_to_dict

router = APIRouter()

_col = settings.mongodb.collections


@router.get("/users/me/bookmarks", response_model=List[BookmarkResponse])
async def get_bookmarks(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    cursor = (
        db[_col.bookmarks]
        .find({"user_id": user_id})
        .sort([("created_at", -1), ("_id", -1)])
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [BookmarkResponse(**document_to_dict(doc)) for doc in docs]


@router.post(
    "/users/me/bookmarks",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_bookmark(
    body: BookmarkCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    now = datetime.now(timezone.utc)
    doc = {"user_id": user_id, "film_id": body.film_id, "created_at": now}
    try:
        result = await db[_col.bookmarks].insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bookmark already exists")
    doc["_id"] = result.inserted_id
    return BookmarkResponse(**document_to_dict(doc))


@router.delete("/users/me/bookmarks/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    film_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    result = await db[_col.bookmarks].delete_one({"user_id": user_id, "film_id": film_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
