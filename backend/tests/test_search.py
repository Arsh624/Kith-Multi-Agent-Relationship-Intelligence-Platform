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
