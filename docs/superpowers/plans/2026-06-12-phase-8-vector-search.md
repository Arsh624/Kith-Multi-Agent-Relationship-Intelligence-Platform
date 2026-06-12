# Kith Phase 8: Vector Search (minimal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semantic search over the user's people: embed people with Gemini, store in Qdrant (local mode), and expose reindex + search endpoints and a small search box.

**Architecture:** An `Embedder` (Gemini real, Fake for tests) and a `VectorStore` (Qdrant local real, Fake in-memory for tests), both injected as dependencies. A service reindexes people and searches; tests run fully hermetic with the fakes. Minimal by design.

**Tech Stack:** FastAPI, google-genai embeddings, qdrant-client (local mode), pytest. Builds on Phases 0 to 7.

---

## Context for the implementer

Phases 0 to 7 complete (69 passing tests). Relevant:
- `app/models/person.py` `Person(id, user_id, name, title, note, company_id)`, `app/models/company.py` `Company(id, name)`.
- `app/config.py` pydantic-settings `Settings` (gemini, neo4j, langfuse fields), `settings = Settings()`.
- `app/deps.py` has `get_current_user`, `get_llm_client`, `get_graph_store` (an `lru_cache` singleton via a private `_build_graph_store`), `get_tracer`. `get_db` in `app/database.py`.
- `app/main.py` imports routers and mounts StaticFiles at "/" as the last lines.
- `tests/conftest.py` has `client`/`db_session`; tests use `app.dependency_overrides` to inject fakes.
- google-genai is installed (`from google import genai`). Run from `backend`: `.\.venv\Scripts\python.exe -m pytest -q`.

No em dashes or en dashes anywhere.

## File Structure (Phase 8)

```
backend/app/search/__init__.py     NEW empty
backend/app/search/embedder.py     NEW Embedder, GeminiEmbedder, FakeEmbedder
backend/app/search/store.py        NEW SearchHit, VectorStore, QdrantVectorStore, FakeVectorStore
backend/app/search/service.py      NEW reindex_people, search_people
backend/app/routers/search.py      NEW POST /search/reindex, GET /search
backend/app/config.py              MODIFY qdrant_path, embedding_model
backend/app/deps.py                MODIFY get_embedder, get_vector_store
backend/app/main.py                MODIFY include search router
backend/requirements.txt           MODIFY add qdrant-client
backend/scripts/smoke_search.py    NEW live smoke
frontend/index.html                MODIFY search box + reindex button
backend/tests/test_search.py       NEW hermetic tests
.gitignore                         MODIFY ignore qdrant_local
```

---

## Task 1: Embedder and vector store (TDD)

**Files:**
- Modify: `backend/requirements.txt`, `.gitignore`, `backend/app/config.py`
- Create: `backend/app/search/__init__.py`, `backend/app/search/embedder.py`, `backend/app/search/store.py`
- Test: `backend/tests/test_search.py` (store/embedder part)

- [ ] **Step 1: Add qdrant-client and install**

Append to `backend/requirements.txt`:
```text
qdrant-client>=1.7,<2
```
Install: `.\.venv\Scripts\python.exe -m pip install "qdrant-client>=1.7,<2"`
Then `.\.venv\Scripts\python.exe -m pip show qdrant-client` and replace the line in requirements.txt with the exact pinned `qdrant-client==X.Y.Z`.

- [ ] **Step 2: Ignore the local Qdrant data dir.** Append to `.gitignore` (project root):
```text
qdrant_local/
```

- [ ] **Step 3: Add settings to `backend/app/config.py`** (with the other fields, before `settings = Settings()`):
```python
    qdrant_path: str = "./qdrant_local"
    embedding_model: str = "text-embedding-004"
```

- [ ] **Step 4: Create `backend/app/search/__init__.py`** (empty)

- [ ] **Step 5: Create `backend/app/search/embedder.py`**

```python
import hashlib
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def embed(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=self._model, contents=text
        )
        return list(result.embeddings[0].values)


class FakeEmbedder:
    DIM = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.DIM
        for word in text.lower().split():
            digest = hashlib.md5(word.encode("utf-8")).hexdigest()
            vector[int(digest, 16) % self.DIM] += 1.0
        return vector
```

- [ ] **Step 6: Create `backend/app/search/store.py`**

```python
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
```

- [ ] **Step 7: Write and run the store/embedder test in `backend/tests/test_search.py`**

```python
from app.search.embedder import FakeEmbedder
from app.search.store import FakeVectorStore


def test_fake_embedder_overlap_scores_higher():
    embedder = FakeEmbedder()
    store = FakeVectorStore()
    store.index("u", "p_designer", embedder.embed("Mia designer Figma"))
    store.index("u", "p_eng", embedder.embed("Bob engineer Stripe"))

    hits = store.search("u", embedder.embed("designer"), 10)
    assert hits[0].person_id == "p_designer"


def test_store_is_scoped_per_user():
    embedder = FakeEmbedder()
    store = FakeVectorStore()
    store.index("owner", "p1", embedder.embed("anything"))
    assert store.search("other", embedder.embed("anything"), 10) == []
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_search.py -v`
Expected: 2 passed.

- [ ] **Step 8: Confirm the whole suite passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 71 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt .gitignore backend/app/config.py backend/app/search/__init__.py backend/app/search/embedder.py backend/app/search/store.py backend/tests/test_search.py
git commit -m "feat: add embedder and qdrant vector store with fakes"
```

---

## Task 2: Search service and endpoints (TDD)

**Files:**
- Create: `backend/app/search/service.py`, `backend/app/routers/search.py`
- Modify: `backend/app/deps.py`, `backend/app/main.py`
- Test: `backend/tests/test_search.py` (service + endpoint part)

- [ ] **Step 1: Create `backend/app/search/service.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.person import Person
from app.search.embedder import Embedder
from app.search.store import VectorStore


def _profile_text(name: str, title, company, note) -> str:
    parts = [name, title or "", company or "", note or ""]
    return ". ".join(p for p in parts if p)


def reindex_people(
    db: Session, user_id: str, embedder: Embedder, store: VectorStore
) -> int:
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()
    for person in people:
        company_name = None
        if person.company_id is not None:
            company = db.get(Company, person.company_id)
            company_name = company.name if company is not None else None
        text = _profile_text(
            person.name, person.title, company_name, person.note
        )
        store.index(user_id, person.id, embedder.embed(text))
    return len(people)


def search_people(
    db: Session,
    user_id: str,
    query: str,
    embedder: Embedder,
    store: VectorStore,
    limit: int = 10,
) -> list[dict]:
    hits = store.search(user_id, embedder.embed(query), limit)
    results = []
    for hit in hits:
        person = db.scalar(
            select(Person).where(
                Person.id == hit.person_id, Person.user_id == user_id
            )
        )
        if person is None:
            continue
        company_name = None
        if person.company_id is not None:
            company = db.get(Company, person.company_id)
            company_name = company.name if company is not None else None
        results.append(
            {
                "id": person.id,
                "name": person.name,
                "title": person.title,
                "company": company_name,
                "score": hit.score,
            }
        )
    return results
```

- [ ] **Step 2: Add dependencies to `backend/app/deps.py`**

Add imports and two providers (the store is a singleton so the local Qdrant client is reused):
```python
from app.search.embedder import Embedder, GeminiEmbedder
from app.search.store import QdrantVectorStore, VectorStore
```
```python
def get_embedder() -> Embedder:
    return GeminiEmbedder(
        api_key=settings.gemini_api_key, model=settings.embedding_model
    )


@lru_cache(maxsize=1)
def _build_vector_store() -> VectorStore:
    return QdrantVectorStore(path=settings.qdrant_path)


def get_vector_store() -> VectorStore:
    return _build_vector_store()
```
Note: `lru_cache` and `settings` are already imported in `deps.py` (used by `get_graph_store`). Reuse them.

- [ ] **Step 3: Create `backend/app/routers/search.py`**

```python
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
```

- [ ] **Step 4: Wire the router into `backend/app/main.py`**

Add `search` to the routers import line and add `app.include_router(search.router)` with the others (before the static mount).

- [ ] **Step 5: Add endpoint tests to `backend/tests/test_search.py`**

Append:
```python
from app.deps import get_embedder, get_vector_store
from app.main import app
from app.search.embedder import FakeEmbedder
from app.search.store import FakeVectorStore


def _register(client, email="se@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_reindex_and_search_endpoints(client):
    headers = _register(client)
    created = client.post(
        "/people", headers=headers, json={"name": "Mia", "company": "Figma"}
    )
    client.patch(
        f"/people/{created.json()['id']}",
        headers=headers,
        json={"title": "designer"},
    )
    client.post("/people", headers=headers, json={"name": "Bob", "company": "Stripe"})

    embedder = FakeEmbedder()
    store = FakeVectorStore()
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_vector_store] = lambda: store
    try:
        reindexed = client.post("/search/reindex", headers=headers)
        assert reindexed.status_code == 200
        assert reindexed.json()["indexed"] == 2

        results = client.get("/search?q=designer", headers=headers).json()["results"]
        assert results[0]["name"] == "Mia"
    finally:
        app.dependency_overrides.pop(get_embedder, None)
        app.dependency_overrides.pop(get_vector_store, None)


def test_search_requires_auth(client):
    assert client.get("/search?q=x").status_code in (401, 403)
    assert client.post("/search/reindex").status_code in (401, 403)
```

- [ ] **Step 6: Run the search tests and the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_search.py -v`
Expected: 4 passed.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 73 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/search/service.py backend/app/routers/search.py backend/app/deps.py backend/app/main.py backend/tests/test_search.py
git commit -m "feat: add reindex and semantic search endpoints"
```

---

## Task 3: Frontend search box and live smoke

**Files:**
- Modify: `frontend/index.html`
- Create: `backend/scripts/smoke_search.py`

- [ ] **Step 1: Add a search row to the Map toolbar**

In `frontend/index.html`, inside the Map `.toolbar` (after the existing Sync button, before the legend span), add:
```html
      <button class="secondary" onclick="reindexSearch()">Reindex search</button>
      <input id="searchQuery" placeholder="search your network by meaning" onkeydown="if(event.key==='Enter')runSearch()" />
      <button onclick="runSearch()">Search</button>
      <span id="searchStatus" class="muted"></span>
```

- [ ] **Step 2: Add the search JS in the `<script>` block**

```javascript
    async function reindexSearch() {
      const status = document.getElementById("searchStatus");
      status.textContent = "Reindexing...";
      try {
        const r = await api("/search/reindex", { method: "POST" });
        status.textContent = "Indexed " + r.indexed + " people.";
      } catch (e) { status.textContent = e.message || "Reindex failed."; }
    }

    async function runSearch() {
      const q = document.getElementById("searchQuery").value.trim();
      if (!q) return;
      const status = document.getElementById("searchStatus");
      status.textContent = "Searching...";
      try {
        const data = await api("/search?q=" + encodeURIComponent(q));
        if (!data.results.length) { status.textContent = "No matches. Try Reindex first."; return; }
        status.textContent = data.results
          .map(function (r) { return r.name + (r.company ? " (" + r.company + ")" : ""); })
          .join(", ");
      } catch (e) { status.textContent = e.message || "Search failed."; }
    }
```

- [ ] **Step 3: Create `backend/scripts/smoke_search.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.search.embedder import GeminiEmbedder
from app.search.store import QdrantVectorStore

PEOPLE = [
    ("p1", "Mia Chen. designer. Figma."),
    ("p2", "Bob Lee. backend engineer. Stripe."),
    ("p3", "Sara Park. recruiter. Notion."),
]


def main() -> None:
    embedder = GeminiEmbedder(
        api_key=settings.gemini_api_key, model=settings.embedding_model
    )
    store = QdrantVectorStore(path="./qdrant_smoke")
    for person_id, text in PEOPLE:
        store.index("smoke-user", person_id, embedder.embed(text))
    hits = store.search("smoke-user", embedder.embed("who is a designer"), 3)
    for hit in hits:
        print(hit.person_id, round(hit.score, 3))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the live smoke (real Gemini embeddings + Qdrant local)**

From the `backend` directory: `.\.venv\Scripts\python.exe -m scripts.smoke_search`
Expected: prints three ids with scores, `p1` (the designer) ranked first. The `qdrant_smoke` dir is created locally; it is ignored if it matches the `qdrant_local` pattern, otherwise delete it after (it is scratch).

- [ ] **Step 5: Confirm the suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 73 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html backend/scripts/smoke_search.py
git commit -m "feat: search box and live qdrant smoke"
```

---

## Self-Review

**Spec coverage:** Gemini embeddings (Task 1 `GeminiEmbedder`), Qdrant local store (Task 1 `QdrantVectorStore`), reindex + search endpoints (Task 2), per-user scoping (store filter + service query), fakes for hermetic tests (Tasks 1 to 2), frontend search box (Task 3), live smoke (Task 3). Deferred items absent.

**Type consistency:** `Embedder.embed(text) -> list[float]` and `VectorStore.index/search` are implemented by both real and fake classes with matching signatures and used consistently in `service.py`, the router, and tests. `SearchHit(person_id, score)` is produced by stores and consumed by `search_people`. `get_embedder`/`get_vector_store` deps match the router parameters and the test overrides.

**Placeholder scan:** No TBDs. Complete code in every step; tests have real assertions and exact counts (69, 71, 73).

**Known pragmatic choices:** Qdrant runs in local on-disk mode (no server/Docker/signup). Reindex is explicit (not automatic on add) to stay minimal. The fake embedder is a deterministic bag-of-words so search tests are real yet hermetic. `query_points` is the current qdrant-client search API; if the installed version lacks it, fall back to `.search(collection_name=..., query_vector=..., query_filter=..., limit=...)` and map `.id`/`.score`.