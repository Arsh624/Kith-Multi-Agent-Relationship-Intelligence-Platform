from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company


def get_or_create_company(db: Session, user_id: str, name: str) -> Company:
    existing = db.scalar(
        select(Company).where(Company.user_id == user_id, Company.name == name)
    )
    if existing is not None:
        return existing
    company = Company(user_id=user_id, name=name)
    db.add(company)
    db.flush()
    return company
