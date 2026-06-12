from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm.base import LLMClient
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person
from app.services.companies import get_or_create_company
from app.services.connections import add_connection
from app.services.resolver import resolve_person


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

    companies_by_name: dict[str, Company] = {}
    for extracted in extraction.companies:
        companies_by_name[extracted.name] = get_or_create_company(
            db, user_id, extracted.name
        )

    people_by_id: dict[str, Person] = {}
    for extracted in extraction.people:
        person = resolve_person(db, user_id, extracted.name)
        company = None
        if extracted.company:
            company = companies_by_name.get(extracted.company)
            if company is None:
                company = get_or_create_company(db, user_id, extracted.company)
                companies_by_name[extracted.company] = company
        if extracted.title and not person.title:
            person.title = extracted.title
        if extracted.note and not person.note:
            person.note = extracted.note
        if company is not None and person.company_id is None:
            person.company_id = company.id
        if not person.source_message_id:
            person.source_message_id = message.id
        people_by_id[person.id] = person

    for relationship in extraction.relationships:
        from_person = resolve_person(db, user_id, relationship.from_person)
        to_person = resolve_person(db, user_id, relationship.to_person)
        for person in (from_person, to_person):
            if not person.source_message_id:
                person.source_message_id = message.id
            people_by_id[person.id] = person
        add_connection(
            db,
            user_id,
            from_person.id,
            to_person.id,
            relationship.relation_type or "knows",
            relationship.note,
            message.id,
        )

    message.processed = True
    db.commit()
    db.refresh(message)
    return IngestResult(
        message=message,
        companies=list(companies_by_name.values()),
        people=list(people_by_id.values()),
    )
