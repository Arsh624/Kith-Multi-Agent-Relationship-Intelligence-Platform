from app.graph.base import (
    GraphSnapshot,
    SnapshotCompany,
    SnapshotConnection,
    SnapshotPerson,
)
from app.graph.fake import FakeGraphStore


def _snapshot():
    return GraphSnapshot(
        people=[
            SnapshotPerson(id="d", name="Dipunj", company_id="cf"),
            SnapshotPerson(id="r", name="Rahul", company_id="qc"),
        ],
        companies=[
            SnapshotCompany(id="cf", name="Cloudflare"),
            SnapshotCompany(id="qc", name="Qualcomm"),
        ],
        connections=[
            SnapshotConnection(from_person_id="d", to_person_id="r", relation_type="knows")
        ],
    )


def test_fake_intro_paths_finds_warm_path():
    store = FakeGraphStore()
    store.sync_user_graph("u1", _snapshot())
    paths = store.intro_paths("u1", "Qualcomm")
    assert ["You", "Dipunj", "Rahul", "Qualcomm"] in paths


def test_fake_intro_paths_empty_for_unknown_company():
    store = FakeGraphStore()
    store.sync_user_graph("u1", _snapshot())
    assert store.intro_paths("u1", "Nowhere") == []


def test_fake_intro_paths_scoped_per_user():
    store = FakeGraphStore()
    store.sync_user_graph("u1", _snapshot())
    assert store.intro_paths("u2", "Qualcomm") == []
