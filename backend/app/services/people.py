from typing import Optional

from sqlalchemy.orm import Session

from app.models.person import Person
from app.services.companies import get_or_create_company
from app.services.connections import add_connection
from app.services.resolver import find_person, resolve_person


class KnownThroughNotFound(Exception):
    """Raised when a known_through person name does not match an existing contact."""


def add_person(
    db: Session,
    user_id: str,
    name: str,
    company_name: Optional[str],
    known_through: Optional[str] = None,
) -> Person:
    person = resolve_person(db, user_id, name)
    if company_name:
        company = get_or_create_company(db, user_id, company_name)
        if person.company_id is None:
            person.company_id = company.id
    if known_through:
        introducer = find_person(db, user_id, known_through)
        if introducer is None:
            raise KnownThroughNotFound(known_through)
        add_connection(db, user_id, introducer.id, person.id, "knows")
    db.commit()
    db.refresh(person)
    return person
