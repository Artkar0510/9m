from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FilmRatingCreate(BaseModel):
    rating: int = Field(..., ge=0, le=10, description="Rating from 0 to 10")


class FilmRatingUpdate(BaseModel):
    rating: int = Field(..., ge=0, le=10)


class FilmRatingResponse(BaseModel):
    id: str
    user_id: str
    film_id: str
    rating: int
    created_at: datetime
    updated_at: datetime


class FilmRatingStats(BaseModel):
    film_id: str
    total_ratings: int
    likes_count: int      # rating >= 6
    dislikes_count: int   # rating <= 4
    neutral_count: int    # rating == 5
    average_rating: Optional[float] = None


class LikedFilm(BaseModel):
    film_id: str
    rating: int
    created_at: datetime
