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


from app.models.company import Company
from app.models.connection import Connection
from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.services.graph_sync import build_snapshot


def _user(db_session):
    user = User(email="g@example.com", hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_build_snapshot_collects_user_graph(db_session):
    user = _user(db_session)
    cf = Company(user_id=user.id, name="Cloudflare")
    qc = Company(user_id=user.id, name="Qualcomm")
    db_session.add_all([cf, qc])
    db_session.flush()
    dipunj = Person(user_id=user.id, name="Dipunj", company_id=cf.id)
    rahul = Person(user_id=user.id, name="Rahul", company_id=qc.id)
    db_session.add_all([dipunj, rahul])
    db_session.flush()
    db_session.add(
        Connection(
            user_id=user.id,
            from_person_id=dipunj.id,
            to_person_id=rahul.id,
            relation_type="knows",
        )
    )
    db_session.commit()

    snapshot = build_snapshot(db_session, user.id)

    assert {p.name for p in snapshot.people} == {"Dipunj", "Rahul"}
    assert {c.name for c in snapshot.companies} == {"Cloudflare", "Qualcomm"}
    assert len(snapshot.connections) == 1
    assert snapshot.connections[0].relation_type == "knows"
