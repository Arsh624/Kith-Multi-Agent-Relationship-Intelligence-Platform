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


def _register(client, email="cc@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_get_and_patch_person_detail(client):
    headers = _register(client)
    created = client.post(
        "/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"}
    )
    person_id = created.json()["id"]

    detail = client.get(f"/people/{person_id}", headers=headers).json()
    assert detail["name"] == "Dipunj"
    assert detail["company"] == "Cloudflare"
    assert detail["email"] is None

    patched = client.patch(
        f"/people/{person_id}",
        headers=headers,
        json={"title": "SDE1", "email": "d@x.com", "linkedin": "in/dipunj"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["title"] == "SDE1"
    assert body["email"] == "d@x.com"
    assert body["linkedin"] == "in/dipunj"

    again = client.patch(
        f"/people/{person_id}", headers=headers, json={"phone": "999"}
    ).json()
    assert again["phone"] == "999"
    assert again["email"] == "d@x.com"
    assert again["title"] == "SDE1"


def test_get_person_detail_unknown_returns_404(client):
    headers = _register(client)
    assert client.get("/people/nope", headers=headers).status_code == 404


def test_person_detail_requires_auth(client):
    assert client.get("/people/x").status_code in (401, 403)
    assert client.patch("/people/x", json={"title": "y"}).status_code in (401, 403)
