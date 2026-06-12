from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.paste import PersonOut
from app.schemas.people import PersonCreate
from app.services.people import add_person

router = APIRouter(tags=["people"])


@router.post(
    "/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED
)
def create_person(
    payload: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = add_person(db, current_user.id, payload.name, payload.company)
    company_name = None
    if person.company_id is not None:
        company = db.get(Company, person.company_id)
        company_name = company.name if company is not None else None
    return PersonOut(
        id=person.id,
        name=person.name,
        title=person.title,
        company=company_name,
        note=person.note,
    )
