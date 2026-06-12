from app.models.company import Company
from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.services.graph_view import build_graph


def _make_user(db_session, email="u@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_build_graph_returns_company_person_and_edge(db_session):
    user = _make_user(db_session)
    company = Company(user_id=user.id, name="Stripe")
    db_session.add(company)
    db_session.flush()
    person = Person(user_id=user.id, name="Priya", company_id=company.id)
    db_session.add(person)
    db_session.commit()

    graph = build_graph(db_session, user.id)

    node_types = {n.label: n.type for n in graph.nodes}
    assert node_types["Stripe"] == "company"
    assert node_types["Priya"] == "person"
    assert any(
        e.label == "WORKS_AT"
        and e.source == f"person:{person.id}"
        and e.target == f"company:{company.id}"
        for e in graph.edges
    )


def test_build_graph_excludes_other_users(db_session):
    owner = _make_user(db_session, email="owner@example.com")
    other = _make_user(db_session, email="other@example.com")
    company = Company(user_id=owner.id, name="Stripe")
    db_session.add(company)
    db_session.commit()

    graph = build_graph(db_session, other.id)

    assert graph.nodes == []
    assert graph.edges == []


def test_build_graph_person_without_company_has_no_edge(db_session):
    user = _make_user(db_session)
    person = Person(user_id=user.id, name="Solo")
    db_session.add(person)
    db_session.commit()

    graph = build_graph(db_session, user.id)

    assert any(n.label == "Solo" and n.type == "person" for n in graph.nodes)
    assert graph.edges == []
