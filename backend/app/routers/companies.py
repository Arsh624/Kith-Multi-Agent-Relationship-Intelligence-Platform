from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.companies import CompanyOut, CompanyPatch
from app.services.companies import delete_company

router = APIRouter(tags=["companies"])


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    payload: CompanyPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.user_id == current_user.id
        )
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )
    if payload.color is not None:
        company.color = payload.color or None
    db.commit()
    db.refresh(company)
    return CompanyOut(id=company.id, name=company.name, color=company.color)


@router.delete(
    "/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_company(db, current_user.id, company_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )
    return None
