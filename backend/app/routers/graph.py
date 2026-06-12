from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.graph import GraphResponse
from app.services.graph_view import build_graph

router = APIRouter(tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
def graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_graph(db, current_user.id)
