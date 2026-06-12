from app.models.user import User
from app.security import hash_password
from app.services.companies import get_or_create_company
from app.services.connections import add_connection
from app.services.resolver import resolve_person


def _make_user(db_session, email="u@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_resolve_person_dedupes_by_normalized_name(db_session):
    user = _make_user(db_session)
    first = resolve_person(db_session, user.id, "Dipunj")
    again = resolve_person(db_session, user.id, "  dipunj ")
    assert first.id == again.id


def test_resolve_person_distinct_names(db_session):
    user = _make_user(db_session)
    a = resolve_person(db_session, user.id, "Dipunj")
    b = resolve_person(db_session, user.id, "Rahul")
    assert a.id != b.id


def test_resolve_person_scoped_per_user(db_session):
    u1 = _make_user(db_session, "a@example.com")
    u2 = _make_user(db_session, "b@example.com")
    p1 = resolve_person(db_session, u1.id, "Dipunj")
    p2 = resolve_person(db_session, u2.id, "Dipunj")
    assert p1.id != p2.id


def test_get_or_create_company_dedupes(db_session):
    user = _make_user(db_session)
    c1 = get_or_create_company(db_session, user.id, "Stripe")
    c2 = get_or_create_company(db_session, user.id, "Stripe")
    assert c1.id == c2.id


def test_add_connection_is_idempotent(db_session):
    user = _make_user(db_session)
    a = resolve_person(db_session, user.id, "Dipunj")
    b = resolve_person(db_session, user.id, "Rahul")
    first = add_connection(db_session, user.id, a.id, b.id, "knows")
    again = add_connection(db_session, user.id, a.id, b.id, "knows")
    assert first.id == again.id
