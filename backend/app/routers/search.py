from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_embedder, get_vector_store
from app.models.user import User
from app.search.embedder import Embedder
from app.search.service import reindex_people, search_people
from app.search.store import VectorStore

router = APIRouter(tags=["search"])


@router.post("/search/reindex")
def reindex(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
):
    count = reindex_people(db, current_user.id, embedder, store)
    return {"indexed": count}


@router.get("/search")
def search(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
):
    results = search_people(db, current_user.id, q, embedder, store)
    return {"query": q, "results": results}
