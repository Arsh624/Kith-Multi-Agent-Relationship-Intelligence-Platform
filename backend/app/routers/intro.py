import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_graph_store
from app.graph.base import GraphStore
from app.models.user import User
from app.services.graph_sync import build_snapshot
from app.services.intro_paths import compute_intro_paths

logger = logging.getLogger(__name__)

router = APIRouter(tags=["graph"])


@router.post("/graph/sync")
def sync_graph(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    store: GraphStore = Depends(get_graph_store),
):
    snapshot = build_snapshot(db, current_user.id)
    # Syncing to Neo4j is a best-effort extra; the app does not depend on it.
    # If the graph database is unreachable, report that instead of failing.
    try:
        store.sync_user_graph(current_user.id, snapshot)
        synced = True
    except Exception as exc:  # noqa: BLE001 - surface a clean status, never 500
        logger.warning("Neo4j sync failed: %s", exc)
        synced = False
    return {
        "synced": synced,
        "people": len(snapshot.people),
        "companies": len(snapshot.companies),
        "connections": len(snapshot.connections),
    }


@router.get("/intro-paths")
def intro_paths(
    company: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Computed from Postgres so it works (and stays fast) regardless of Neo4j.
    snapshot = build_snapshot(db, current_user.id)
    paths = compute_intro_paths(snapshot, company)
    return {"company": company, "paths": paths}
