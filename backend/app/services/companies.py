from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.person import Person


def get_or_create_company(db: Session, user_id: str, name: str) -> Company:
    normalized = name.strip().lower()
    existing = db.scalar(
        select(Company).where(
            Company.user_id == user_id,
            func.lower(func.trim(Company.name)) == normalized,
        )
    )
    if existing is not None:
        return existing
    company = Company(user_id=user_id, name=name.strip())
    db.add(company)
    db.flush()
    return company


def delete_company(db: Session, user_id: str, company_id: str) -> bool:
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.user_id == user_id
        )
    )
    if company is None:
        return False
    people = db.scalars(
        select(Person).where(
            Person.user_id == user_id, Person.company_id == company_id
        )
    ).all()
    for person in people:
        person.company_id = None
    db.delete(company)
    db.commit()
    return True
