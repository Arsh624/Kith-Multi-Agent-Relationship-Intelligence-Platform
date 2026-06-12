from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.services.contacts import get_contact, upsert_contact


def _make_user(db_session, email="c@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_person(db_session, user_id, name="Dipunj"):
    person = Person(user_id=user_id, name=name)
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)
    return person


def test_upsert_creates_then_updates_only_given_fields(db_session):
    user = _make_user(db_session)
    person = _make_person(db_session, user.id)

    upsert_contact(db_session, user.id, person.id, email="d@x.com", phone="123")
    db_session.commit()
    contact = get_contact(db_session, user.id, person.id)
    assert contact.email == "d@x.com"
    assert contact.phone == "123"
    assert contact.linkedin is None

    upsert_contact(db_session, user.id, person.id, linkedin="in/dipunj")
    db_session.commit()
    contact = get_contact(db_session, user.id, person.id)
    assert contact.email == "d@x.com"
    assert contact.linkedin == "in/dipunj"


def test_get_contact_scoped_to_user(db_session):
    owner = _make_user(db_session, "owner@example.com")
    other = _make_user(db_session, "other@example.com")
    person = _make_person(db_session, owner.id)
    upsert_contact(db_session, owner.id, person.id, email="d@x.com")
    db_session.commit()
    assert get_contact(db_session, other.id, person.id) is None
