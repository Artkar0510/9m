from httpx import AsyncClient

FILM_ID = "film-test-001"
FILM_ID_2 = "film-test-002"


async def test_stats_empty_film(client: AsyncClient):
    r = await client.get(f"/api/v1/films/{FILM_ID}/ratings/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ratings"] == 0
    assert data["average_rating"] is None
    assert data["likes_count"] == 0
    assert data["dislikes_count"] == 0


async def test_upsert_rating_create(client: AsyncClient):
    r = await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 8})
    assert r.status_code == 200
    data = r.json()
    assert data["rating"] == 8
    assert data["film_id"] == FILM_ID
    assert "id" in data
    assert "created_at" in data


async def test_upsert_rating_update(client: AsyncClient):
    await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 8})
    r = await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 3})
    assert r.status_code == 200
    assert r.json()["rating"] == 3


async def test_stats_after_rating(client: AsyncClient):
    await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 8})
    r = await client.get(f"/api/v1/films/{FILM_ID}/ratings/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_ratings"] == 1
    assert data["likes_count"] == 1
    assert data["dislikes_count"] == 0
    assert data["average_rating"] == 8.0


async def test_stats_like_dislike_neutral(client: AsyncClient):
    await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 7})
    r = await client.get(f"/api/v1/films/{FILM_ID}/ratings/stats")
    data = r.json()
    assert data["likes_count"] == 1
    assert data["dislikes_count"] == 0
    assert data["neutral_count"] == 0


async def test_delete_rating(client: AsyncClient):
    await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 8})
    r = await client.delete(f"/api/v1/films/{FILM_ID}/ratings")
    assert r.status_code == 204


async def test_delete_rating_not_found(client: AsyncClient):
    r = await client.delete(f"/api/v1/films/{FILM_ID}/ratings")
    assert r.status_code == 404


async def test_liked_films_list(client: AsyncClient):
    await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 8})
    await client.post(f"/api/v1/films/{FILM_ID_2}/ratings", json={"rating": 3})
    r = await client.get("/api/v1/users/me/liked-films")
    assert r.status_code == 200
    films = r.json()
    assert len(films) == 1
    assert films[0]["film_id"] == FILM_ID


async def test_liked_films_empty(client: AsyncClient):
    r = await client.get("/api/v1/users/me/liked-films")
    assert r.status_code == 200
    assert r.json() == []


async def test_rating_validation_above_max(client: AsyncClient):
    r = await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": 11})
    assert r.status_code == 422


async def test_rating_validation_below_min(client: AsyncClient):
    r = await client.post(f"/api/v1/films/{FILM_ID}/ratings", json={"rating": -1})
    assert r.status_code == 422
