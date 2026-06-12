from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact


def get_contact(
    db: Session, user_id: str, person_id: str
) -> Optional[Contact]:
    return db.scalar(
        select(Contact).where(
            Contact.user_id == user_id, Contact.person_id == person_id
        )
    )


def upsert_contact(
    db: Session,
    user_id: str,
    person_id: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin: Optional[str] = None,
) -> Contact:
    contact = get_contact(db, user_id, person_id)
    if contact is None:
        contact = Contact(user_id=user_id, person_id=person_id)
        db.add(contact)
    if email is not None:
        contact.email = email
    if phone is not None:
        contact.phone = phone
    if linkedin is not None:
        contact.linkedin = linkedin
    db.flush()
    return contact
