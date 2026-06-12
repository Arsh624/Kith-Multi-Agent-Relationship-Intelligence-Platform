from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.companies import delete_company

router = APIRouter(tags=["companies"])


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
