from httpx import AsyncClient

FILM_ID_1 = "film-bm-001"
FILM_ID_2 = "film-bm-002"
FILM_ID_3 = "film-bm-003"


async def test_add_bookmark(client: AsyncClient):
    r = await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_1})
    assert r.status_code == 201
    data = r.json()
    assert data["film_id"] == FILM_ID_1
    assert "id" in data
    assert "created_at" in data


async def test_add_duplicate_bookmark(client: AsyncClient):
    await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_1})
    r = await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_1})
    assert r.status_code == 409


async def test_get_bookmarks_empty(client: AsyncClient):
    r = await client.get("/api/v1/users/me/bookmarks")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_bookmarks_list(client: AsyncClient):
    await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_1})
    await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_2})
    r = await client.get("/api/v1/users/me/bookmarks")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    film_ids = {b["film_id"] for b in data}
    assert FILM_ID_1 in film_ids
    assert FILM_ID_2 in film_ids


async def test_get_bookmarks_sorted_by_date_desc(client: AsyncClient):
    await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_1})
    await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_2})
    r = await client.get("/api/v1/users/me/bookmarks")
    data = r.json()
    assert data[0]["film_id"] == FILM_ID_2


async def test_delete_bookmark(client: AsyncClient):
    await client.post("/api/v1/users/me/bookmarks", json={"film_id": FILM_ID_1})
    r = await client.delete(f"/api/v1/users/me/bookmarks/{FILM_ID_1}")
    assert r.status_code == 204
    r2 = await client.get("/api/v1/users/me/bookmarks")
    assert r2.json() == []


async def test_delete_nonexistent_bookmark(client: AsyncClient):
    r = await client.delete(f"/api/v1/users/me/bookmarks/{FILM_ID_3}")
    assert r.status_code == 404


async def test_bookmarks_multiple_films(client: AsyncClient):
    for film_id in [FILM_ID_1, FILM_ID_2, FILM_ID_3]:
        await client.post("/api/v1/users/me/bookmarks", json={"film_id": film_id})
    r = await client.get("/api/v1/users/me/bookmarks")
    assert len(r.json()) == 3
