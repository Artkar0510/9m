from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.v1 import bookmarks, likes, reviews
from core.settings import settings
from db.mongodb import close_mongo_connection, connect_to_mongo
from utils.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    app.state.http_client = httpx.AsyncClient()
    app.state.redis = aioredis.from_url(settings.redis.url, decode_responses=True)
    yield
    await close_mongo_connection()
    await app.state.http_client.aclose()
    await app.state.redis.aclose()


app = FastAPI(
    title="UGC Service",
    description="User-Generated Content: likes/ratings, reviews, bookmarks",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(likes.router, prefix="/api/v1", tags=["Likes & Ratings"])
app.include_router(reviews.router, prefix="/api/v1", tags=["Reviews"])
app.include_router(bookmarks.router, prefix="/api/v1", tags=["Bookmarks"])
