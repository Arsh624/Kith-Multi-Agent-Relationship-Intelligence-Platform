from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.base import LLMClient
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person


@dataclass
class IngestResult:
    message: Message
    companies: list[Company]
    people: list[Person]


def ingest_message(
    db: Session, user_id: str, source: str, text: str, llm: LLMClient
) -> IngestResult:
    message = Message(user_id=user_id, source=source, raw_text=text)
    db.add(message)
    db.flush()

    extraction = llm.extract_entities(text)

    company_by_name: dict[str, Company] = {}
    for extracted in extraction.companies:
        company_by_name[extracted.name] = _get_or_create_company(
            db, user_id, extracted.name
        )

    people: list[Person] = []
    for extracted in extraction.people:
        company = None
        if extracted.company:
            company = company_by_name.get(extracted.company)
            if company is None:
                company = _get_or_create_company(db, user_id, extracted.company)
                company_by_name[extracted.company] = company
        person = Person(
            user_id=user_id,
            name=extracted.name,
            title=extracted.title,
            note=extracted.note,
            company_id=company.id if company is not None else None,
            source_message_id=message.id,
        )
        db.add(person)
        people.append(person)

    message.processed = True
    db.commit()
    db.refresh(message)
    return IngestResult(
        message=message, companies=list(company_by_name.values()), people=people
    )


def _get_or_create_company(db: Session, user_id: str, name: str) -> Company:
    existing = db.scalar(
        select(Company).where(Company.user_id == user_id, Company.name == name)
    )
    if existing is not None:
        return existing
    company = Company(user_id=user_id, name=name)
    db.add(company)
    db.flush()
    return company
