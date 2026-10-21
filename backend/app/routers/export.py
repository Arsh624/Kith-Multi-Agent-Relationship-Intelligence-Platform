from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.company import Company
from app.models.connection import Connection
from app.models.contact import Contact
from app.models.person import Person
from app.models.task import Task
from app.models.user import User

router = APIRouter(tags=["export"])


@router.get("/export")
def export_my_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A full, read-only snapshot of the signed-in user's data, for backup."""
    uid = current_user.id
    people = db.scalars(select(Person).where(Person.user_id == uid)).all()
    companies = db.scalars(select(Company).where(Company.user_id == uid)).all()
    connections = db.scalars(
        select(Connection).where(Connection.user_id == uid)
    ).all()
    tasks = db.scalars(select(Task).where(Task.user_id == uid)).all()
    contacts = db.scalars(select(Contact).where(Contact.user_id == uid)).all()

    company_name = {c.id: c.name for c in companies}
    person_name = {p.id: p.name for p in people}
    contact_by_person = {c.person_id: c for c in contacts}

    def person_row(p: Person) -> dict:
        contact = contact_by_person.get(p.id)
        return {
            "name": p.name,
            "title": p.title,
            "company": company_name.get(p.company_id),
            "note": p.note,
            "status": p.status,
            "color": p.color,
            "favorite": bool(p.favorite),
            "email": contact.email if contact is not None else None,
            "phone": contact.phone if contact is not None else None,
            "linkedin": contact.linkedin if contact is not None else None,
        }

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": current_user.email,
        "people": [person_row(p) for p in people],
        "companies": [
            {"name": c.name, "color": c.color} for c in companies
        ],
        "connections": [
            {
                "from": person_name.get(c.from_person_id),
                "to": person_name.get(c.to_person_id),
                "relation": c.relation_type,
            }
            for c in connections
        ],
        "tasks": [
            {
                "title": t.title,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "priority": t.priority,
                "done": bool(t.done),
            }
            for t in tasks
        ],
    }
