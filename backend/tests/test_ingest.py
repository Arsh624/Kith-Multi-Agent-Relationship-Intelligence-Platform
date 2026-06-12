from sqlalchemy import select

from app.models.company import Company
from app.models.person import Person
from app.models.user import User
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
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


def test_ingest_creates_message_people_and_companies(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(
                    name="Priya Sharma",
                    title="PM",
                    company="Stripe",
                    note="offered intro",
                )
            ],
        )
    )

    result = ingest_message(db_session, user.id, "email", "raw text", fake)

    assert result.message.processed is True
    assert len(result.companies) == 1
    assert result.companies[0].name == "Stripe"
    assert len(result.people) == 1

    person = db_session.scalars(select(Person)).one()
    assert person.name == "Priya Sharma"
    assert person.title == "PM"
    assert person.note == "offered intro"
    assert person.company_id == result.companies[0].id
    assert person.source_message_id == result.message.id


def test_ingest_dedupes_companies_within_one_message(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(name="A", company="Stripe"),
                ExtractedPerson(name="B", company="Stripe"),
            ],
        )
    )

    ingest_message(db_session, user.id, "email", "raw", fake)

    companies = db_session.scalars(select(Company)).all()
    assert len(companies) == 1
