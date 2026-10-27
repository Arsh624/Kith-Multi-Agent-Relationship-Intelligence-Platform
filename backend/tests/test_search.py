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


class CountingEmbedder(FakeEmbedder):
    """Counts how many profile texts get embedded (queries go through embed)."""

    def __init__(self) -> None:
        self.profiles_embedded = 0

    def embed_many(self, texts):
        self.profiles_embedded += len(texts)
        return super().embed_many(texts)


def _with_search_fakes(embedder, store):
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_vector_store] = lambda: store


def _clear_search_fakes():
    app.dependency_overrides.pop(get_embedder, None)
    app.dependency_overrides.pop(get_vector_store, None)


def test_search_works_on_empty_index_without_manual_reindex(client):
    # Mirrors production: Render wipes the on-disk Qdrant index on every deploy,
    # so search must rebuild missing vectors from Postgres instead of returning [].
    headers = _register(client, "fresh@example.com")
    created = client.post(
        "/people", headers=headers, json={"name": "Mia", "company": "Figma"}
    )
    client.patch(
        f"/people/{created.json()['id']}", headers=headers, json={"title": "designer"}
    )
    client.post("/people", headers=headers, json={"name": "Bob", "company": "Stripe"})

    _with_search_fakes(FakeEmbedder(), FakeVectorStore())
    try:
        results = client.get("/search?q=designer", headers=headers).json()["results"]
        assert results and results[0]["name"] == "Mia"
    finally:
        _clear_search_fakes()


def test_search_finds_person_added_after_last_index(client):
    headers = _register(client, "late@example.com")
    client.post("/people", headers=headers, json={"name": "Bob", "company": "Stripe"})
    _with_search_fakes(FakeEmbedder(), FakeVectorStore())
    try:
        client.post("/search/reindex", headers=headers)
        zoe = client.post(
            "/people", headers=headers, json={"name": "Zoe", "company": "Notion"}
        )
        client.patch(
            f"/people/{zoe.json()['id']}", headers=headers, json={"title": "recruiter"}
        )
        results = client.get("/search?q=recruiter", headers=headers).json()["results"]
        assert "Zoe" in [r["name"] for r in results]
    finally:
        _clear_search_fakes()


def test_search_only_embeds_people_not_yet_indexed(client):
    headers = _register(client, "cheap@example.com")
    client.post("/people", headers=headers, json={"name": "Mia", "company": "Figma"})
    client.post("/people", headers=headers, json={"name": "Bob", "company": "Stripe"})
    embedder = CountingEmbedder()
    _with_search_fakes(embedder, FakeVectorStore())
    try:
        client.get("/search?q=figma", headers=headers)
        assert embedder.profiles_embedded == 2
        client.get("/search?q=stripe", headers=headers)
        assert embedder.profiles_embedded == 2  # nothing re-embedded
    finally:
        _clear_search_fakes()


def test_qdrant_store_reports_indexed_ids_per_user(tmp_path):
    from app.search.store import QdrantVectorStore

    store = QdrantVectorStore(path=str(tmp_path / "q"))
    assert store.indexed_ids("u1") == set()  # no collection yet, as on a fresh deploy
    a, b = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
    store.index("u1", a, [1.0, 0.0, 0.0])
    store.index("u2", b, [0.0, 1.0, 0.0])
    assert store.indexed_ids("u1") == {a}
    assert store.indexed_ids("u2") == {b}
