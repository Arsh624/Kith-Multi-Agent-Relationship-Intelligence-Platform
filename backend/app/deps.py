from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.graph.base import GraphStore
from app.graph.neo4j_store import Neo4jGraphStore
from app.llm.base import LLMClient
from app.llm.gemini import GeminiClient
from app.models.user import User
from app.observability.tracer import get_tracer
from app.search.embedder import Embedder, GeminiEmbedder
from app.search.store import QdrantVectorStore, VectorStore
from app.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def get_llm_client() -> LLMClient:
    fallbacks = (
        [settings.gemini_fallback_model] if settings.gemini_fallback_model else []
    )
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        fallback_models=fallbacks,
        tracer=get_tracer(),
    )


@lru_cache(maxsize=1)
def _build_graph_store() -> GraphStore:
    return Neo4jGraphStore(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )


def get_graph_store() -> GraphStore:
    return _build_graph_store()


def get_embedder() -> Embedder:
    return GeminiEmbedder(
        api_key=settings.gemini_api_key, model=settings.embedding_model
    )


@lru_cache(maxsize=1)
def _build_vector_store() -> VectorStore:
    return QdrantVectorStore(path=settings.qdrant_path)


def get_vector_store() -> VectorStore:
    return _build_vector_store()
