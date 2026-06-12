from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_llm_client
from app.llm.base import LLMClient
from app.models.user import User
from app.schemas.paste import CompanyOut, PasteRequest, PasteResponse, PersonOut
from app.services.ingest import ingest_message

router = APIRouter(tags=["ingest"])


@router.post("/paste", response_model=PasteResponse, status_code=status.HTTP_201_CREATED)
def paste(
    payload: PasteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
):
    result = ingest_message(
        db, current_user.id, payload.source, payload.text, llm
    )
    company_name_by_id = {c.id: c.name for c in result.companies}
    companies = [CompanyOut(id=c.id, name=c.name) for c in result.companies]
    people = [
        PersonOut(
            id=p.id,
            name=p.name,
            title=p.title,
            company=company_name_by_id.get(p.company_id),
            note=p.note,
        )
        for p in result.people
    ]
    return PasteResponse(
        message_id=result.message.id, companies=companies, people=people
    )
