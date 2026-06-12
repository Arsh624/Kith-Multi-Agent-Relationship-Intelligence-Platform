from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.person import Person


def resolve_person(db: Session, user_id: str, name: str) -> Person:
    normalized = name.strip().lower()
    existing = db.scalar(
        select(Person).where(
            Person.user_id == user_id,
            func.lower(func.trim(Person.name)) == normalized,
        )
    )
    if existing is not None:
        return existing
    person = Person(user_id=user_id, name=name.strip())
    db.add(person)
    db.flush()
    return person
