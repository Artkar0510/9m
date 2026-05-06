from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from api.v1 import bookmarks, likes, reviews
from db.mongodb import close_mongo_connection, connect_to_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    app.state.http_client = httpx.AsyncClient()
    yield
    await close_mongo_connection()
    await app.state.http_client.aclose()


app = FastAPI(
    title="UGC Service",
    description="User-Generated Content: likes/ratings, reviews, bookmarks",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(likes.router, prefix="/api/v1", tags=["Likes & Ratings"])
app.include_router(reviews.router, prefix="/api/v1", tags=["Reviews"])
app.include_router(bookmarks.router, prefix="/api/v1", tags=["Bookmarks"])
