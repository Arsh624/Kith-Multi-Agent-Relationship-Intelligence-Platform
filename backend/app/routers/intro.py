from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_graph_store
from app.graph.base import GraphStore
from app.models.user import User
from app.services.graph_sync import build_snapshot

router = APIRouter(tags=["graph"])


@router.post("/graph/sync")
def sync_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    store: GraphStore = Depends(get_graph_store),
):
    snapshot = build_snapshot(db, current_user.id)
    store.sync_user_graph(current_user.id, snapshot)
    return {
        "people": len(snapshot.people),
        "companies": len(snapshot.companies),
        "connections": len(snapshot.connections),
    }


@router.get("/intro-paths")
def intro_paths(
    company: str,
    current_user: User = Depends(get_current_user),
    store: GraphStore = Depends(get_graph_store),
):
    paths = store.intro_paths(current_user.id, company)
    return {"company": company, "paths": paths}
