import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class SearchHit:
    person_id: str
    score: float


@runtime_checkable
class VectorStore(Protocol):
    def index(self, user_id: str, person_id: str, vector: list[float]) -> None:
        ...

    def search(
        self, user_id: str, vector: list[float], limit: int
    ) -> list[SearchHit]:
        ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class FakeVectorStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, list[float]]] = {}

    def index(self, user_id: str, person_id: str, vector: list[float]) -> None:
        self._data.setdefault(user_id, {})[person_id] = vector

    def search(
        self, user_id: str, vector: list[float], limit: int
    ) -> list[SearchHit]:
        items = self._data.get(user_id, {})
        scored = [
            SearchHit(person_id=pid, score=_cosine(vector, vec))
            for pid, vec in items.items()
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]


class QdrantVectorStore:
    def __init__(self, path: str, collection: str = "people") -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(path=path)
        self._collection = collection

    def _ensure(self, dim: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        names = [c.name for c in self._client.get_collections().collections]
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def index(self, user_id: str, person_id: str, vector: list[float]) -> None:
        from qdrant_client.models import PointStruct

        self._ensure(len(vector))
        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=person_id, vector=vector, payload={"user_id": user_id}
                )
            ],
        )

    def search(
        self, user_id: str, vector: list[float], limit: int
    ) -> list[SearchHit]:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        self._ensure(len(vector))
        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id", match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit,
        )
        return [
            SearchHit(person_id=str(point.id), score=point.score)
            for point in response.points
        ]
