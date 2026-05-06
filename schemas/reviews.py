from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SortBy(str, Enum):
    published_at = "published_at"
    likes_count = "likes_count"
    film_rating = "film_rating"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class ReviewCreate(BaseModel):
    text: str
    film_rating: Optional[int] = Field(None, ge=0, le=10)


class ReviewLikeCreate(BaseModel):
    is_like: bool


class ReviewLikeResponse(BaseModel):
    id: str
    review_id: str
    user_id: str
    is_like: bool
    created_at: datetime


class ReviewResponse(BaseModel):
    id: str
    film_id: str
    author: str
    text: str
    film_rating: Optional[int] = None
    published_at: datetime
    likes_count: int
    dislikes_count: int
