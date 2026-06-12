# Kith Phase 4: Neo4j Warm Paths Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mirror the relationship graph into Neo4j and answer "who can get me into <company>?" by returning warm paths (You to a contact to ... to someone who works there).

**Architecture:** A `GraphStore` interface with an in-memory `FakeGraphStore` (used by all tests, so the suite needs no Neo4j) and a real `Neo4jGraphStore` (Aura, official driver). `POST /graph/sync` rebuilds the user's Neo4j subgraph from Postgres (the source of truth); `GET /intro-paths` runs the multi-hop query. The frontend gets an intro-paths search and auto-syncs after changes.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, `neo4j` Python driver (Aura), vis-network frontend, pytest. Builds on Phases 0 to 3.

---

## Context for the implementer

Phases 0 to 3 are complete (39 passing tests). Relevant existing code:
- Models `app/models/{person,company,connection}.py` (Person: id, name, company_id; Company: id, name; Connection: from_person_id, to_person_id, relation_type), all per `user_id`.
- `app/deps.py` has `get_current_user` and `get_llm_client` (pattern to copy for `get_graph_store`).
- `app/config.py` has a `settings` object; `tests/conftest.py` sets env vars before importing app, has `client` and `db_session` fixtures.
- `backend/.env` (gitignored) already contains `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` for the real Aura instance. Never print them.
- Run from `backend`: `.\.venv\Scripts\python.exe -m pytest -q`.

No em dashes or en dashes anywhere.

## File Structure (Phase 4)

```
backend/app/graph/__init__.py        NEW: empty
backend/app/graph/base.py            NEW: GraphStore ABC + GraphSnapshot dataclasses
backend/app/graph/fake.py            NEW: FakeGraphStore (in-memory BFS)
backend/app/graph/neo4j_store.py     NEW: Neo4jGraphStore (driver + Cypher)
backend/app/config.py                MODIFY: neo4j_* settings
backend/tests/conftest.py            MODIFY: dummy neo4j env vars
backend/app/services/graph_sync.py   NEW: build_snapshot(db, user_id)
backend/app/deps.py                  MODIFY: get_graph_store
backend/app/routers/intro.py         NEW: POST /graph/sync, GET /intro-paths
backend/app/main.py                  MODIFY: include intro router
frontend/index.html                  MODIFY: intro-paths box + auto-sync
backend/scripts/smoke_neo4j.py       NEW: live Aura smoke test
backend/requirements.txt             MODIFY: add neo4j
backend/tests/test_intro.py          NEW: fake store + endpoint tests
```

---

## Task 1: Dependency and config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add the neo4j driver and install it**

Append to `backend/requirements.txt`:
```text
neo4j>=5.0.0
```
Install: `.\.venv\Scripts\python.exe -m pip install "neo4j>=5.0.0"`
Then pin the exact installed version: `.\.venv\Scripts\python.exe -m pip show neo4j`, and replace the `neo4j>=5.0.0` line with `neo4j==X.Y.Z`.

- [ ] **Step 2: Verify import**

Run: `.\.venv\Scripts\python.exe -c "from neo4j import GraphDatabase; print('neo4j ok')"`
Expected: `neo4j ok`.

- [ ] **Step 3: Add neo4j settings to `backend/app/config.py`**

Add four fields after `gemini_fallback_model` so the class body includes:
```python
    gemini_fallback_model: str = "gemini-2.0-flash"
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    neo4j_database: str = ""
```

- [ ] **Step 4: Add dummy neo4j env vars to `backend/tests/conftest.py`**

In the top os.environ block (before `import pytest`), add:
```python
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test"
os.environ["NEO4J_DATABASE"] = "neo4j"
```

- [ ] **Step 5: Confirm the suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 39 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/tests/conftest.py
git commit -m "feat: add neo4j driver and connection settings"
```

---

## Task 2: GraphStore interface and FakeGraphStore (TDD)

**Files:**
- Create: `backend/app/graph/__init__.py` (empty)
- Create: `backend/app/graph/base.py`
- Create: `backend/app/graph/fake.py`
- Test: `backend/tests/test_intro.py`

- [ ] **Step 1: Create the empty package file `backend/app/graph/__init__.py`** (no content)

- [ ] **Step 2: Create `backend/app/graph/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SnapshotPerson:
    id: str
    name: str
    company_id: Optional[str]


@dataclass
class SnapshotCompany:
    id: str
    name: str


@dataclass
class SnapshotConnection:
    from_person_id: str
    to_person_id: str
    relation_type: str


@dataclass
class GraphSnapshot:
    people: list[SnapshotPerson] = field(default_factory=list)
    companies: list[SnapshotCompany] = field(default_factory=list)
    connections: list[SnapshotConnection] = field(default_factory=list)


class GraphStore(ABC):
    @abstractmethod
    def sync_user_graph(self, user_id: str, snapshot: GraphSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def intro_paths(
        self, user_id: str, company_name: str, max_hops: int = 4
    ) -> list[list[str]]:
        raise NotImplementedError
```

- [ ] **Step 3: Write the failing tests `backend/tests/test_intro.py`**

```python
from app.graph.base import (
    GraphSnapshot,
    SnapshotCompany,
    SnapshotConnection,
    SnapshotPerson,
)
from app.graph.fake import FakeGraphStore


def _snapshot():
    return GraphSnapshot(
        people=[
            SnapshotPerson(id="d", name="Dipunj", company_id="cf"),
            SnapshotPerson(id="r", name="Rahul", company_id="qc"),
        ],
        companies=[
            SnapshotCompany(id="cf", name="Cloudflare"),
            SnapshotCompany(id="qc", name="Qualcomm"),
        ],
        connections=[
            SnapshotConnection(from_person_id="d", to_person_id="r", relation_type="knows")
        ],
    )


def test_fake_intro_paths_finds_warm_path():
    store = FakeGraphStore()
    store.sync_user_graph("u1", _snapshot())
    paths = store.intro_paths("u1", "Qualcomm")
    assert ["You", "Dipunj", "Rahul", "Qualcomm"] in paths


def test_fake_intro_paths_empty_for_unknown_company():
    store = FakeGraphStore()
    store.sync_user_graph("u1", _snapshot())
    assert store.intro_paths("u1", "Nowhere") == []


def test_fake_intro_paths_scoped_per_user():
    store = FakeGraphStore()
    store.sync_user_graph("u1", _snapshot())
    assert store.intro_paths("u2", "Qualcomm") == []
```

- [ ] **Step 4: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_intro.py -v`
Expected: import error (`app.graph.fake` missing).

- [ ] **Step 5: Create `backend/app/graph/fake.py`**

```python
from collections import deque

from app.graph.base import GraphSnapshot, GraphStore


class FakeGraphStore(GraphStore):
    def __init__(self) -> None:
        self._snapshots: dict[str, GraphSnapshot] = {}

    def sync_user_graph(self, user_id: str, snapshot: GraphSnapshot) -> None:
        self._snapshots[user_id] = snapshot

    def intro_paths(
        self, user_id: str, company_name: str, max_hops: int = 4
    ) -> list[list[str]]:
        snapshot = self._snapshots.get(user_id)
        if snapshot is None:
            return []

        people = {p.id: p for p in snapshot.people}
        company_name_by_id = {c.id: c.name for c in snapshot.companies}
        target = company_name.strip().lower()

        adjacency: dict[str, list[str]] = {}
        incoming: set[str] = set()
        for connection in snapshot.connections:
            adjacency.setdefault(connection.from_person_id, []).append(
                connection.to_person_id
            )
            incoming.add(connection.to_person_id)

        def company_of(person_id: str) -> str:
            person = people.get(person_id)
            if person is None or person.company_id is None:
                return ""
            return (company_name_by_id.get(person.company_id) or "").strip().lower()

        first_degree = [p.id for p in snapshot.people if p.id not in incoming]

        results: list[list[str]] = []
        queue: deque[list[str]] = deque([fid] for fid in first_degree)
        while queue:
            path = queue.popleft()
            current = path[-1]
            if company_of(current) == target:
                company = company_name_by_id.get(people[current].company_id)
                results.append(
                    ["You"] + [people[pid].name for pid in path] + [company]
                )
            if len(path) >= max_hops:
                continue
            for nxt in adjacency.get(current, []):
                if nxt not in path:
                    queue.append(path + [nxt])

        results.sort(key=len)
        return results[:5]
```

- [ ] **Step 6: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_intro.py -v`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/graph/__init__.py backend/app/graph/base.py backend/app/graph/fake.py backend/tests/test_intro.py
git commit -m "feat: add GraphStore interface and in-memory FakeGraphStore with tests"
```

---

## Task 3: Snapshot builder (TDD)

**Files:**
- Create: `backend/app/services/graph_sync.py`
- Test: `backend/tests/test_intro.py`

- [ ] **Step 1: Add the failing test to `backend/tests/test_intro.py`**

Append:
```python
from app.models.company import Company
from app.models.connection import Connection
from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.services.graph_sync import build_snapshot


def _user(db_session):
    user = User(email="g@example.com", hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_build_snapshot_collects_user_graph(db_session):
    user = _user(db_session)
    cf = Company(user_id=user.id, name="Cloudflare")
    qc = Company(user_id=user.id, name="Qualcomm")
    db_session.add_all([cf, qc])
    db_session.flush()
    dipunj = Person(user_id=user.id, name="Dipunj", company_id=cf.id)
    rahul = Person(user_id=user.id, name="Rahul", company_id=qc.id)
    db_session.add_all([dipunj, rahul])
    db_session.flush()
    db_session.add(
        Connection(
            user_id=user.id,
            from_person_id=dipunj.id,
            to_person_id=rahul.id,
            relation_type="knows",
        )
    )
    db_session.commit()

    snapshot = build_snapshot(db_session, user.id)

    assert {p.name for p in snapshot.people} == {"Dipunj", "Rahul"}
    assert {c.name for c in snapshot.companies} == {"Cloudflare", "Qualcomm"}
    assert len(snapshot.connections) == 1
    assert snapshot.connections[0].relation_type == "knows"
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_intro.py -v`
Expected: import error (`app.services.graph_sync` missing).

- [ ] **Step 3: Create `backend/app/services/graph_sync.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.base import (
    GraphSnapshot,
    SnapshotCompany,
    SnapshotConnection,
    SnapshotPerson,
)
from app.models.company import Company
from app.models.connection import Connection
from app.models.person import Person


def build_snapshot(db: Session, user_id: str) -> GraphSnapshot:
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()
    companies = db.scalars(
        select(Company).where(Company.user_id == user_id)
    ).all()
    connections = db.scalars(
        select(Connection).where(Connection.user_id == user_id)
    ).all()

    return GraphSnapshot(
        people=[
            SnapshotPerson(id=p.id, name=p.name, company_id=p.company_id)
            for p in people
        ],
        companies=[SnapshotCompany(id=c.id, name=c.name) for c in companies],
        connections=[
            SnapshotConnection(
                from_person_id=c.from_person_id,
                to_person_id=c.to_person_id,
                relation_type=c.relation_type,
            )
            for c in connections
        ],
    )
```

- [ ] **Step 4: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_intro.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/graph_sync.py backend/tests/test_intro.py
git commit -m "feat: build a graph snapshot from Postgres for syncing"
```

---

## Task 4: get_graph_store, the endpoints, and wiring (TDD)

**Files:**
- Create: `backend/app/graph/neo4j_store.py` (stub needed so `deps` imports cleanly; full body in Task 5)
- Modify: `backend/app/deps.py`
- Create: `backend/app/routers/intro.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_intro.py`

- [ ] **Step 1: Create `backend/app/graph/neo4j_store.py` with the full implementation**

(This is created now so `deps.py` can import it; it is only exercised live by the smoke test in Task 7.)
```python
from app.graph.base import GraphSnapshot, GraphStore

_ALLOWED_RELATIONS = {"KNOWS", "REFERRED", "CAN_INTRO"}


class Neo4jGraphStore(GraphStore):
    def __init__(
        self, uri: str, username: str, password: str, database: str = ""
    ) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        self._database = database or None

    def close(self) -> None:
        self._driver.close()

    def sync_user_graph(self, user_id: str, snapshot: GraphSnapshot) -> None:
        incoming = {c.to_person_id for c in snapshot.connections}
        with self._driver.session(database=self._database) as session:
            session.execute_write(self._rebuild, user_id, snapshot, incoming)

    @staticmethod
    def _rebuild(tx, user_id, snapshot, incoming):
        tx.run("MATCH (n {user_id: $uid}) DETACH DELETE n", uid=user_id)
        tx.run("MERGE (y:You {user_id: $uid}) SET y.name = 'You'", uid=user_id)
        for company in snapshot.companies:
            tx.run(
                "CREATE (c:Company {id: $id, name: $name, user_id: $uid})",
                id=company.id,
                name=company.name,
                uid=user_id,
            )
        for person in snapshot.people:
            tx.run(
                "CREATE (p:Person {id: $id, name: $name, user_id: $uid})",
                id=person.id,
                name=person.name,
                uid=user_id,
            )
            if person.company_id:
                tx.run(
                    "MATCH (p:Person {id: $pid, user_id: $uid}), "
                    "(c:Company {id: $cid, user_id: $uid}) "
                    "CREATE (p)-[:WORKS_AT]->(c)",
                    pid=person.id,
                    cid=person.company_id,
                    uid=user_id,
                )
            if person.id not in incoming:
                tx.run(
                    "MATCH (y:You {user_id: $uid}), "
                    "(p:Person {id: $pid, user_id: $uid}) "
                    "CREATE (y)-[:KNOWS]->(p)",
                    uid=user_id,
                    pid=person.id,
                )
        for connection in snapshot.connections:
            rel = connection.relation_type.upper()
            if rel not in _ALLOWED_RELATIONS:
                rel = "KNOWS"
            tx.run(
                "MATCH (a:Person {id: $f, user_id: $uid}), "
                "(b:Person {id: $t, user_id: $uid}) "
                f"CREATE (a)-[:{rel}]->(b)",
                f=connection.from_person_id,
                t=connection.to_person_id,
                uid=user_id,
            )

    def intro_paths(self, user_id, company_name, max_hops=4):
        query = (
            "MATCH path = (y:You {user_id: $uid})"
            "-[:KNOWS|REFERRED|CAN_INTRO*1..%d]->(p:Person)"
            "-[:WORKS_AT]->(c:Company) "
            "WHERE c.user_id = $uid AND toLower(c.name) = toLower($company) "
            "RETURN [n IN nodes(path) | n.name] AS names "
            "ORDER BY length(path) LIMIT 5" % int(max_hops)
        )
        with self._driver.session(database=self._database) as session:
            result = session.run(query, uid=user_id, company=company_name)
            return [record["names"] for record in result]
```

- [ ] **Step 2: Add `get_graph_store` to `backend/app/deps.py`**

Add these imports near the top and the function at the end:
```python
from app.graph.base import GraphStore
from app.graph.neo4j_store import Neo4jGraphStore


def get_graph_store() -> GraphStore:
    return Neo4jGraphStore(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
```

- [ ] **Step 3: Write the failing endpoint tests in `backend/tests/test_intro.py`**

Append:
```python
from app.deps import get_graph_store
from app.main import app


def _register(client, email="i@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return response.json()["access_token"]


def test_sync_then_intro_paths_endpoint(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"})
    client.post(
        "/people",
        headers=headers,
        json={"name": "Rahul", "company": "Qualcomm", "known_through": "Dipunj"},
    )

    store = FakeGraphStore()
    app.dependency_overrides[get_graph_store] = lambda: store
    try:
        sync = client.post("/graph/sync", headers=headers)
        assert sync.status_code == 200
        assert sync.json()["people"] == 2

        response = client.get("/intro-paths?company=Qualcomm", headers=headers)
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert ["You", "Dipunj", "Rahul", "Qualcomm"] in paths
    finally:
        app.dependency_overrides.pop(get_graph_store, None)


def test_intro_paths_requires_auth(client):
    response = client.get("/intro-paths?company=Qualcomm")
    assert response.status_code in (401, 403)
```

- [ ] **Step 4: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_intro.py -v`
Expected: the endpoint tests fail with 404 (routes not wired).

- [ ] **Step 5: Create `backend/app/routers/intro.py`**

```python
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
```

- [ ] **Step 6: Wire the router into `backend/app/main.py`**

Add `intro` to the routers import and include it. The import line becomes:
```python
from app.routers import auth, graph, health, intro, paste, people
```
And add after the other `include_router` calls (before the static mount):
```python
app.include_router(intro.router)
```

- [ ] **Step 7: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_intro.py -v`
Expected: 6 passed.

- [ ] **Step 8: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 47 passed (39 plus the 8 in test_intro.py).

- [ ] **Step 9: Commit**

```bash
git add backend/app/graph/neo4j_store.py backend/app/deps.py backend/app/routers/intro.py backend/app/main.py backend/tests/test_intro.py
git commit -m "feat: add graph sync and intro-paths endpoints with tests"
```

---

## Task 5: Frontend intro-paths search and auto-sync

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add an intro-paths row to the toolbar**

In `frontend/index.html`, find the legend span at the end of the toolbar:
```html
      <span class="legend">
```
Insert this block immediately before that `<span class="legend">` line:
```html
      <input id="introCompany" placeholder="who can get me into... (company)" onkeydown="if(event.key==='Enter')findPaths()" />
      <button onclick="findPaths()">Find paths</button>
      <button class="secondary" onclick="syncGraph()">Sync</button>
      <span id="pathStatus" class="muted"></span>
```

- [ ] **Step 2: Add `syncGraph`, `findPaths`, and auto-sync calls in the script**

Find the `addPerson` function. Immediately after it, add:
```javascript
    async function syncGraph() {
      try { await api("/graph/sync", { method: "POST" }); } catch (e) {}
    }

    async function findPaths() {
      const company = document.getElementById("introCompany").value.trim();
      const status = document.getElementById("pathStatus");
      if (!company) { status.textContent = "Enter a company."; return; }
      status.textContent = "Syncing and searching...";
      try {
        await api("/graph/sync", { method: "POST" });
        const result = await api("/intro-paths?company=" + encodeURIComponent(company));
        if (!result.paths.length) {
          status.textContent = "No warm path to " + company + " found.";
          return;
        }
        const lines = result.paths.map(function (p) { return p.join(" -> "); });
        status.textContent = "Paths: " + lines.join("  |  ");
      } catch (e) { status.textContent = e.message || "Search failed."; }
    }
```

- [ ] **Step 3: Auto-sync after adding a person**

In `addPerson`, the success branch currently ends with `loadGraph();` inside the `try`. Change that line to:
```javascript
        loadGraph();
        syncGraph();
```

- [ ] **Step 4: Auto-sync after a paste**

In `paste`, the success branch also ends with `loadGraph();`. Change it to:
```javascript
        loadGraph();
        syncGraph();
```

- [ ] **Step 5: Confirm the suite still passes (frontend-only change)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 47 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: intro-paths search and auto-sync in the map UI"
```

---

## Task 6: Live Aura smoke test

**Files:**
- Create: `backend/scripts/smoke_neo4j.py`

This verifies the real Aura connection and the Cypher path query. It uses the credentials in `backend/.env`. Manual, not part of the hermetic suite.

- [ ] **Step 1: Create `backend/scripts/smoke_neo4j.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.graph.base import (
    GraphSnapshot,
    SnapshotCompany,
    SnapshotConnection,
    SnapshotPerson,
)
from app.graph.neo4j_store import Neo4jGraphStore

USER = "smoke-test-user"


def main() -> None:
    store = Neo4jGraphStore(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    snapshot = GraphSnapshot(
        people=[
            SnapshotPerson(id="d", name="Dipunj", company_id="cf"),
            SnapshotPerson(id="r", name="Rahul", company_id="qc"),
        ],
        companies=[
            SnapshotCompany(id="cf", name="Cloudflare"),
            SnapshotCompany(id="qc", name="Qualcomm"),
        ],
        connections=[
            SnapshotConnection(from_person_id="d", to_person_id="r", relation_type="knows")
        ],
    )
    store.sync_user_graph(USER, snapshot)
    print("intro paths to Qualcomm:", store.intro_paths(USER, "Qualcomm"))
    store.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it against Aura**

Run (from `backend`): `.\.venv\Scripts\python.exe scripts\smoke_neo4j.py`
Expected: prints `intro paths to Qualcomm: [['You', 'Dipunj', 'Rahul', 'Qualcomm']]`. If it errors on connection, the `.env` Neo4j values are wrong or the instance is paused; report the error WITHOUT printing the password.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_neo4j.py
git commit -m "chore: add live Aura smoke test for the graph store"
```

---

## Task 7: End-to-end verification (live, real Aura)

**Files:** none (verification only).

- [ ] **Step 1: Start the app on a fresh SQLite database in the background**

From `backend` (PowerShell, background):
```
$env:DATABASE_URL = "sqlite:///./kith_p4.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
(The Neo4j values are read from `.env` regardless of `DATABASE_URL`.)

- [ ] **Step 2: Register, add the chain, sync, query the path**

```
$reg = Invoke-RestMethod -Uri http://localhost:8000/auth/register -Method Post -ContentType application/json -Body '{"email":"p4@example.com","password":"hunter2"}'
$h = @{ Authorization = "Bearer " + $reg.access_token }
Invoke-RestMethod -Uri http://localhost:8000/people -Method Post -ContentType application/json -Headers $h -Body '{"name":"Dipunj","company":"Cloudflare"}' | Out-Null
Invoke-RestMethod -Uri http://localhost:8000/people -Method Post -ContentType application/json -Headers $h -Body '{"name":"Rahul","company":"Qualcomm","known_through":"Dipunj"}' | Out-Null
Invoke-RestMethod -Uri http://localhost:8000/graph/sync -Method Post -Headers $h | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/intro-paths?company=Qualcomm" -Method Get -Headers $h | ConvertTo-Json -Depth 6
```
Expected: sync returns counts; intro-paths returns a `paths` array containing `["You","Dipunj","Rahul","Qualcomm"]`.

- [ ] **Step 3: Stop the background server.**

- [ ] **Step 4: Manual browser check**

Tell the user to run the app, add Dipunj then Rahul (known through Dipunj), type "Qualcomm" in the intro box, click "Find paths", and confirm the path shows.

- [ ] **Step 5: Commit any fixes** with a clear message if verification required changes. `kith_p4.db` is gitignored.

---

## Self-Review

**Spec coverage:** GraphStore interface + Fake + Neo4j (Tasks 2, 4). `POST /graph/sync` and `GET /intro-paths` (Task 4). `get_graph_store` dependency (Task 4). Snapshot builder (Task 3). neo4j dep + settings (Task 1). Frontend search + auto-sync (Task 5). Live smoke test (Task 6) and live E2E (Task 7). Hermetic tests via FakeGraphStore throughout. Deferred items (write-through, path visualization, Qdrant) correctly absent.

**Type consistency:** `GraphStore.sync_user_graph(user_id, snapshot)` and `intro_paths(user_id, company_name, max_hops=4) -> list[list[str]]` are defined in Task 2 and implemented identically by `FakeGraphStore` (Task 2) and `Neo4jGraphStore` (Task 4). `GraphSnapshot` / `SnapshotPerson(id,name,company_id)` / `SnapshotCompany(id,name)` / `SnapshotConnection(from_person_id,to_person_id,relation_type)` are used consistently in `build_snapshot` (Task 3), the fake (Task 2), the neo4j store (Task 4), and the smoke test (Task 6). `build_snapshot(db, user_id) -> GraphSnapshot` matches its call in the router (Task 4). The intro router uses `get_graph_store` defined in Task 4.

**Placeholder scan:** No TBDs. Every code step is complete; test steps have real assertions and exact counts (39, then 47).

**Known pragmatic choices:** Neo4j is rebuilt per-user on sync (no incremental write-through), so a Neo4j outage never breaks adds or pastes. `Neo4jGraphStore` is created in Task 4 (so `deps` imports) but only exercised live in Tasks 6 and 7; the hermetic suite always uses `FakeGraphStore`. Relationship-type interpolation into Cypher is constrained to a fixed allow-list. The Aura free instance can pause when idle; the first call may need a few seconds.
