from sqlalchemy import select

from app.models.connection import Connection
from app.models.person import Person
from app.models.user import User
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractedRelationship,
    ExtractionResult,
)
from app.security import hash_password
from app.services.ingest import ingest_message
from tests.fakes import FakeLLMClient


def _make_user(db_session):
    user = User(email="u@example.com", hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_ingest_creates_connection_between_people(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Qualcomm")],
            people=[
                ExtractedPerson(name="Dipunj", company="Cloudflare"),
                ExtractedPerson(name="Rahul", company="Qualcomm"),
            ],
            relationships=[
                ExtractedRelationship(
                    from_person="Dipunj", to_person="Rahul", relation_type="knows"
                )
            ],
        )
    )

    ingest_message(db_session, user.id, "email", "raw", fake)

    people = {p.name: p for p in db_session.scalars(select(Person)).all()}
    connection = db_session.scalars(select(Connection)).one()
    assert connection.from_person_id == people["Dipunj"].id
    assert connection.to_person_id == people["Rahul"].id
    assert connection.relation_type == "knows"


def test_ingest_dedupes_people_across_pastes(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(people=[ExtractedPerson(name="Dipunj")])
    )
    ingest_message(db_session, user.id, "email", "first", fake)
    ingest_message(db_session, user.id, "email", "second", fake)

    dipunjs = db_session.scalars(
        select(Person).where(Person.name == "Dipunj")
    ).all()
    assert len(dipunjs) == 1
