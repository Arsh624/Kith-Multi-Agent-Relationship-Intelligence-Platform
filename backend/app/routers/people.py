from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.company import Company
from app.models.person import Person
from app.models.user import User
from app.schemas.paste import PersonOut
from app.schemas.people import PersonCreate, PersonDetail, PersonPatch
from app.services.contacts import get_contact, upsert_contact
from app.services.people import KnownThroughNotFound, add_person, delete_person

router = APIRouter(tags=["people"])


@router.post(
    "/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED
)
def create_person(
    payload: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        person = add_person(
            db, current_user.id, payload.name, payload.company, payload.known_through
        )
    except KnownThroughNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The 'known through' person was not found. Add them first.",
        )
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


@router.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_person(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_person(db, current_user.id, person_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )
    return None


def _build_detail(db: Session, user_id: str, person: Person) -> PersonDetail:
    company_name = None
    if person.company_id is not None:
        company = db.get(Company, person.company_id)
        company_name = company.name if company is not None else None
    contact = get_contact(db, user_id, person.id)
    return PersonDetail(
        id=person.id,
        name=person.name,
        title=person.title,
        company=company_name,
        note=person.note,
        email=contact.email if contact is not None else None,
        phone=contact.phone if contact is not None else None,
        linkedin=contact.linkedin if contact is not None else None,
        color=person.color,
        favorite=bool(person.favorite),
    )


@router.get("/people/{person_id}", response_model=PersonDetail)
def person_detail(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.scalar(
        select(Person).where(
            Person.id == person_id, Person.user_id == current_user.id
        )
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )
    return _build_detail(db, current_user.id, person)


@router.patch("/people/{person_id}", response_model=PersonDetail)
def update_person_detail(
    person_id: str,
    payload: PersonPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.scalar(
        select(Person).where(
            Person.id == person_id, Person.user_id == current_user.id
        )
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )
    if payload.title is not None:
        person.title = payload.title
    if payload.color is not None:
        person.color = payload.color or None
    if payload.favorite is not None:
        person.favorite = payload.favorite
    upsert_contact(
        db,
        current_user.id,
        person_id,
        payload.email,
        payload.phone,
        payload.linkedin,
    )
    db.commit()
    db.refresh(person)
    return _build_detail(db, current_user.id, person)
