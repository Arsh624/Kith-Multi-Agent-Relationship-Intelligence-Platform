from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.person import Person


def add_person(
    db: Session, user_id: str, name: str, company_name: Optional[str]
) -> Person:
    company = None
    if company_name:
        company = db.scalar(
            select(Company).where(
                Company.user_id == user_id, Company.name == company_name
            )
        )
        if company is None:
            company = Company(user_id=user_id, name=company_name)
            db.add(company)
            db.flush()

    person = Person(
        user_id=user_id,
        name=name,
        company_id=company.id if company is not None else None,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person
