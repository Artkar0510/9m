from httpx import AsyncClient

FILM_ID = "film-review-001"


async def _create_review(client: AsyncClient, text: str = "Great movie!", rating: int = 8):
    r = await client.post(
        f"/api/v1/films/{FILM_ID}/reviews",
        json={"text": text, "film_rating": rating},
    )
    assert r.status_code == 201
    return r.json()


async def test_create_review(client: AsyncClient):
    r = await client.post(
        f"/api/v1/films/{FILM_ID}/reviews",
        json={"text": "Amazing film!", "film_rating": 9},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["film_id"] == FILM_ID
    assert data["author"] == "TestUser"
    assert data["text"] == "Amazing film!"
    assert data["film_rating"] == 9
    assert data["likes_count"] == 0
    assert data["dislikes_count"] == 0
    assert "id" in data
    assert "published_at" in data


async def test_create_review_without_rating(client: AsyncClient):
    r = await client.post(
        f"/api/v1/films/{FILM_ID}/reviews",
        json={"text": "Interesting."},
    )
    assert r.status_code == 201
    assert r.json()["film_rating"] is None


async def test_get_review_by_id(client: AsyncClient):
    created = await _create_review(client)
    review_id = created["id"]
    r = await client.get(f"/api/v1/reviews/{review_id}")
    assert r.status_code == 200
    assert r.json()["id"] == review_id


async def test_get_review_invalid_id(client: AsyncClient):
    r = await client.get("/api/v1/reviews/not-valid-id")
    assert r.status_code == 400


async def test_get_review_not_found(client: AsyncClient):
    r = await client.get("/api/v1/reviews/000000000000000000000000")
    assert r.status_code == 404


async def test_list_reviews_empty(client: AsyncClient):
    r = await client.get(f"/api/v1/films/{FILM_ID}/reviews")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_reviews_sorted_by_date(client: AsyncClient):
    await _create_review(client, text="First review")
    await _create_review(client, text="Second review")
    r = await client.get(f"/api/v1/films/{FILM_ID}/reviews?sort_by=published_at&order=desc")
    assert r.status_code == 200
    reviews = r.json()
    assert len(reviews) == 2
    assert reviews[0]["text"] == "Second review"


async def test_list_reviews_pagination(client: AsyncClient):
    for i in range(5):
        await _create_review(client, text=f"Review {i}")
    r = await client.get(f"/api/v1/films/{FILM_ID}/reviews?limit=3&skip=0")
    assert len(r.json()) == 3
    r2 = await client.get(f"/api/v1/films/{FILM_ID}/reviews?limit=3&skip=3")
    assert len(r2.json()) == 2


async def test_add_like_to_review(client: AsyncClient):
    review = await _create_review(client)
    review_id = review["id"]
    r = await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": True})
    assert r.status_code == 200
    data = r.json()
    assert data["is_like"] is True
    assert data["review_id"] == review_id

    stats = await client.get(f"/api/v1/reviews/{review_id}")
    assert stats.json()["likes_count"] == 1
    assert stats.json()["dislikes_count"] == 0


async def test_add_dislike_to_review(client: AsyncClient):
    review = await _create_review(client)
    review_id = review["id"]
    await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": False})
    stats = await client.get(f"/api/v1/reviews/{review_id}")
    assert stats.json()["dislikes_count"] == 1
    assert stats.json()["likes_count"] == 0


async def test_toggle_like_to_dislike(client: AsyncClient):
    review = await _create_review(client)
    review_id = review["id"]
    await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": True})
    await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": False})
    stats = await client.get(f"/api/v1/reviews/{review_id}")
    data = stats.json()
    assert data["likes_count"] == 0
    assert data["dislikes_count"] == 1


async def test_idempotent_like(client: AsyncClient):
    review = await _create_review(client)
    review_id = review["id"]
    await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": True})
    await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": True})
    stats = await client.get(f"/api/v1/reviews/{review_id}")
    assert stats.json()["likes_count"] == 1


async def test_delete_review_like(client: AsyncClient):
    review = await _create_review(client)
    review_id = review["id"]
    await client.post(f"/api/v1/reviews/{review_id}/likes", json={"is_like": True})
    r = await client.delete(f"/api/v1/reviews/{review_id}/likes")
    assert r.status_code == 204
    stats = await client.get(f"/api/v1/reviews/{review_id}")
    assert stats.json()["likes_count"] == 0


async def test_delete_nonexistent_like(client: AsyncClient):
    review = await _create_review(client)
    r = await client.delete(f"/api/v1/reviews/{review['id']}/likes")
    assert r.status_code == 404


async def test_list_reviews_sorted_by_likes(client: AsyncClient):
    r1 = await _create_review(client, text="Popular review")
    r2 = await _create_review(client, text="Less popular review")
    await client.post(f"/api/v1/reviews/{r1['id']}/likes", json={"is_like": True})

    r = await client.get(f"/api/v1/films/{FILM_ID}/reviews?sort_by=likes_count&order=desc")
    reviews = r.json()
    assert reviews[0]["text"] == "Popular review"
