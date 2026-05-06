from datetime import datetime

from pydantic import BaseModel


class BookmarkCreate(BaseModel):
    film_id: str


class BookmarkResponse(BaseModel):
    id: str
    user_id: str
    film_id: str
    created_at: datetime
