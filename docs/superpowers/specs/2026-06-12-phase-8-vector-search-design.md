# Kith Phase 8: Vector Search (minimal)

**Design spec** · 2026-06-12

## Purpose

Add semantic search over your network ("who do I know in fintech?") using Gemini
embeddings stored in Qdrant. Deliberately minimal: enough to be a real, tested feature and
to honestly cover the Qdrant / vector-search box, no more.

## Scope

### In scope (Phase 8)
- Embed each person's profile text (name, role, company, note) with Gemini embeddings and
  store the vectors in Qdrant (qdrant-client local on-disk mode, so no server, no Docker,
  no signup, $0).
- `POST /search/reindex`: embed all of the signed-in user's people into Qdrant.
- `GET /search?q=...`: embed the query, return the top matching people (id, name, score).
- A small search box on the Map that lists matches.

### Explicitly deferred
- Auto-reindex on every add (reindex is an explicit call for now).
- Searching messages or notes as separate documents; semantic dedup of people.
- Gmail auto-sync and anything else.

## Success criteria
- After reindex, `GET /search?q="designer"` ranks a person whose note says "designer at
  Figma" above unrelated people.
- Per-user scoped (a query only returns your own people).
- Hermetic tests pass with a fake embedder and a fake in-memory store (no Gemini, no Qdrant
  needed to run tests).
- A live smoke against real Gemini embeddings + Qdrant local confirms end to end.

## Architecture

### Embedder (`app/search/embedder.py`)
- `Embedder` protocol: `embed(text: str) -> list[float]`.
- `GeminiEmbedder`: uses google-genai `embed_content` (model `text-embedding-004`).
- `FakeEmbedder`: deterministic bag-of-words vector over a fixed hashed vocabulary, so
  texts sharing words get similar vectors (used by tests).

### Vector store (`app/search/store.py`)
- `SearchHit(person_id, score)`.
- `VectorStore` protocol: `index(user_id, person_id, vector)`, `search(user_id, vector,
  limit) -> list[SearchHit]`.
- `QdrantVectorStore`: qdrant-client in local mode (`QdrantClient(path=...)`), one
  collection, `user_id` in the payload and used as a filter; creates the collection lazily
  from the first vector's dimension.
- `FakeVectorStore`: in-memory dict plus cosine similarity, scoped by user (used by tests).

### Service (`app/search/service.py`)
- `reindex_people(db, user_id, embedder, store)`: for each person build
  `"{name}. {title}. {company}. {note}"`, embed, and index.
- `search_people(db, user_id, query, embedder, store, limit=10) -> list[dict]`: embed the
  query, search the store, then load the matching `Person` rows (scoped per user) and
  return `[{id, name, title, company, score}]` in rank order.

### Endpoints (`app/routers/search.py`)
- `POST /search/reindex` (JWT) -> `{ "indexed": n }`.
- `GET /search?q=...` (JWT) -> `{ "query": q, "results": [...] }`.

### Config and deps
- `settings` gains `qdrant_path` (default `./qdrant_local`) and `embedding_model`
  (default `text-embedding-004`). `get_embedder()` and `get_vector_store()` dependencies
  (the store is an lru_cache singleton so the local Qdrant client is reused). Tests override
  both with the fakes.

### Frontend
- A search input plus button on the Map toolbar: a "Reindex" button (calls
  `POST /search/reindex`) and a search box that calls `GET /search` and lists the matching
  people with their company and score.

## Testing
- `search_people` with a `FakeEmbedder` and `FakeVectorStore`: index three people, a query
  overlapping one person's text ranks that person first; results are scoped per user.
- Endpoints with both deps overridden by fakes: reindex returns a count; search returns the
  expected person first; auth required.
- Live smoke `backend/scripts/smoke_search.py`: reindex a couple of people with real Gemini
  embeddings into Qdrant local and run a query. Manual.

## Files (planned)
```
backend/app/search/__init__.py
backend/app/search/embedder.py     Embedder, GeminiEmbedder, FakeEmbedder
backend/app/search/store.py        SearchHit, VectorStore, QdrantVectorStore, FakeVectorStore
backend/app/search/service.py      reindex_people, search_people
backend/app/routers/search.py      POST /search/reindex, GET /search
backend/app/config.py              qdrant_path, embedding_model
backend/app/deps.py                get_embedder, get_vector_store
backend/app/main.py                include search router
backend/requirements.txt           add qdrant-client
frontend/index.html                search box + reindex button
backend/scripts/smoke_search.py    live smoke
backend/tests/test_search.py       hermetic tests
```
