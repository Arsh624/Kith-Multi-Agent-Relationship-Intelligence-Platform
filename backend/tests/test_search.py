from app.search.embedder import FakeEmbedder
from app.search.store import FakeVectorStore


def test_fake_embedder_overlap_scores_higher():
    embedder = FakeEmbedder()
    store = FakeVectorStore()
    store.index("u", "p_designer", embedder.embed("Mia designer Figma"))
    store.index("u", "p_eng", embedder.embed("Bob engineer Stripe"))

    hits = store.search("u", embedder.embed("designer"), 10)
    assert hits[0].person_id == "p_designer"


def test_store_is_scoped_per_user():
    embedder = FakeEmbedder()
    store = FakeVectorStore()
    store.index("owner", "p1", embedder.embed("anything"))
    assert store.search("other", embedder.embed("anything"), 10) == []


from app.deps import get_embedder, get_vector_store
from app.main import app
from app.search.embedder import FakeEmbedder
from app.search.store import FakeVectorStore


def _register(client, email="se@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_reindex_and_search_endpoints(client):
    headers = _register(client)
    created = client.post(
        "/people", headers=headers, json={"name": "Mia", "company": "Figma"}
    )
    client.patch(
        f"/people/{created.json()['id']}",
        headers=headers,
        json={"title": "designer"},
    )
    client.post("/people", headers=headers, json={"name": "Bob", "company": "Stripe"})

    embedder = FakeEmbedder()
    store = FakeVectorStore()
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_vector_store] = lambda: store
    try:
        reindexed = client.post("/search/reindex", headers=headers)
        assert reindexed.status_code == 200
        assert reindexed.json()["indexed"] == 2

        results = client.get("/search?q=designer", headers=headers).json()["results"]
        assert results[0]["name"] == "Mia"
    finally:
        app.dependency_overrides.pop(get_embedder, None)
        app.dependency_overrides.pop(get_vector_store, None)


def test_search_requires_auth(client):
    assert client.get("/search?q=x").status_code in (401, 403)
    assert client.post("/search/reindex").status_code in (401, 403)
