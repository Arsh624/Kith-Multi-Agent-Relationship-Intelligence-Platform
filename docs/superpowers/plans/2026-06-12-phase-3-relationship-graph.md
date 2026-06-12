# Kith Phase 3: Relationship Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture person-to-person relationships (you know Dipunj, Dipunj knows Rahul), deduplicate people with a Resolver, and render a `You`-centered graph where a second-degree contact links to both the person who connects you and their own company.

**Architecture:** A new Postgres `connections` table holds directed person-to-person edges. A Resolver merges people by normalized name so the same person is one node. Connections are created from a new "known through" field on manual add and from relationships the Extractor now returns. `GET /graph` adds a synthetic `You` node linked to first-degree contacts plus the relationship edges. Postgres stays the source of truth; Neo4j and the warm-path query are the next phase.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Gemini (structured output), Cytoscape/vis-network frontend, pytest. Builds on Phases 0 to 2.

---

## Context for the implementer

Phases 0 to 2 are complete (30 passing tests). Relevant existing code:
- Models: `app/models/{user,company,message,person}.py`; all registered in `app/models/__init__.py`.
- Services: `app/services/ingest.py` (`ingest_message`, `IngestResult`, private `_get_or_create_company`), `app/services/people.py` (`add_person`), `app/services/graph_view.py` (`build_graph`).
- Schemas: `app/schemas/extraction.py` (`ExtractedCompany`, `ExtractedPerson`, `ExtractionResult`), `app/schemas/paste.py` (`PersonOut`, etc.), `app/schemas/people.py` (`PersonCreate`), `app/schemas/graph.py` (`GraphNode`, `GraphEdge`, `GraphResponse`).
- LLM: `app/llm/gemini.py` (`GeminiClient`, `EXTRACTION_PROMPT`), `app/llm/base.py`, `app/llm/errors.py`.
- Routers: `auth`, `health`, `paste`, `graph`, `people`.
- Tests use `client` and `db_session` fixtures in `tests/conftest.py`; `tests/fakes.py` has `FakeLLMClient`.
- Run from the `backend` directory: `.\.venv\Scripts\python.exe -m pytest -q`.

No em dashes or en dashes anywhere (code, comments, commit messages).

## File Structure (Phase 3)

```
backend/app/models/connection.py        NEW: Connection ORM
backend/app/models/__init__.py          MODIFY: register Connection
backend/app/services/companies.py       NEW: get_or_create_company (extracted, shared)
backend/app/services/resolver.py        NEW: resolve_person (normalized-name dedup)
backend/app/services/connections.py     NEW: add_connection (idempotent)
backend/app/schemas/extraction.py       MODIFY: ExtractedRelationship + relationships
backend/app/llm/gemini.py               MODIFY: prompt mentions relationships
backend/app/services/ingest.py          MODIFY: use resolver + companies + connections
backend/app/schemas/people.py           MODIFY: known_through on PersonCreate
backend/app/services/people.py          MODIFY: use resolver, handle known_through
backend/app/routers/people.py           MODIFY: pass known_through
backend/app/services/graph_view.py      MODIFY: You node + relationship edges
frontend/index.html                     MODIFY: known-through input + edge/You styling
backend/tests/test_services.py          NEW: resolver, companies, connections
backend/tests/test_relationships.py     NEW: ingest relationships + known_through
backend/tests/test_graph_view.py        MODIFY: You node expectations
backend/tests/test_graph.py             MODIFY: You node expectations
backend/tests/test_people.py            MODIFY: graph edge expectation
```

---

## Task 1: Connection model

**Files:**
- Create: `backend/app/models/connection.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/connection.py`**

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    from_person_id: Mapped[str] = mapped_column(
        String, ForeignKey("people.id"), nullable=False, index=True
    )
    to_person_id: Mapped[str] = mapped_column(
        String, ForeignKey("people.id"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(
        String, nullable=False, default="knows"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_message_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("messages.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Register it in `backend/app/models/__init__.py`**

Replace the file with:
```python
from app.models.user import User
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person
from app.models.connection import Connection

__all__ = ["User", "Company", "Message", "Person", "Connection"]
```

- [ ] **Step 3: Verify the table registers**

Run: `.\.venv\Scripts\python.exe -c "import app.models; from app.database import Base; print(sorted(Base.metadata.tables))"`
Expected: `['companies', 'connections', 'messages', 'people', 'users']`.

- [ ] **Step 4: Confirm the suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 30 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/connection.py backend/app/models/__init__.py
git commit -m "feat: add Connection model for person to person edges"
```

---

## Task 2: Service helpers (Resolver, companies, connections) with TDD

**Files:**
- Create: `backend/app/services/companies.py`
- Create: `backend/app/services/resolver.py`
- Create: `backend/app/services/connections.py`
- Test: `backend/tests/test_services.py`

- [ ] **Step 1: Write the failing tests `backend/tests/test_services.py`**

```python
from app.models.user import User
from app.security import hash_password
from app.services.companies import get_or_create_company
from app.services.connections import add_connection
from app.services.resolver import resolve_person


def _make_user(db_session, email="u@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_resolve_person_dedupes_by_normalized_name(db_session):
    user = _make_user(db_session)
    first = resolve_person(db_session, user.id, "Dipunj")
    again = resolve_person(db_session, user.id, "  dipunj ")
    assert first.id == again.id


def test_resolve_person_distinct_names(db_session):
    user = _make_user(db_session)
    a = resolve_person(db_session, user.id, "Dipunj")
    b = resolve_person(db_session, user.id, "Rahul")
    assert a.id != b.id


def test_resolve_person_scoped_per_user(db_session):
    u1 = _make_user(db_session, "a@example.com")
    u2 = _make_user(db_session, "b@example.com")
    p1 = resolve_person(db_session, u1.id, "Dipunj")
    p2 = resolve_person(db_session, u2.id, "Dipunj")
    assert p1.id != p2.id


def test_get_or_create_company_dedupes(db_session):
    user = _make_user(db_session)
    c1 = get_or_create_company(db_session, user.id, "Stripe")
    c2 = get_or_create_company(db_session, user.id, "Stripe")
    assert c1.id == c2.id


def test_add_connection_is_idempotent(db_session):
    user = _make_user(db_session)
    a = resolve_person(db_session, user.id, "Dipunj")
    b = resolve_person(db_session, user.id, "Rahul")
    first = add_connection(db_session, user.id, a.id, b.id, "knows")
    again = add_connection(db_session, user.id, a.id, b.id, "knows")
    assert first.id == again.id
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_services.py -v`
Expected: import errors (the service modules do not exist yet).

- [ ] **Step 3: Create `backend/app/services/companies.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company


def get_or_create_company(db: Session, user_id: str, name: str) -> Company:
    existing = db.scalar(
        select(Company).where(Company.user_id == user_id, Company.name == name)
    )
    if existing is not None:
        return existing
    company = Company(user_id=user_id, name=name)
    db.add(company)
    db.flush()
    return company
```

- [ ] **Step 4: Create `backend/app/services/resolver.py`**

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.person import Person


def resolve_person(db: Session, user_id: str, name: str) -> Person:
    normalized = name.strip().lower()
    existing = db.scalar(
        select(Person).where(
            Person.user_id == user_id,
            func.lower(func.trim(Person.name)) == normalized,
        )
    )
    if existing is not None:
        return existing
    person = Person(user_id=user_id, name=name.strip())
    db.add(person)
    db.flush()
    return person
```

- [ ] **Step 5: Create `backend/app/services/connections.py`**

```python
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connection import Connection


def add_connection(
    db: Session,
    user_id: str,
    from_person_id: str,
    to_person_id: str,
    relation_type: str = "knows",
    note: Optional[str] = None,
    source_message_id: Optional[str] = None,
) -> Connection:
    existing = db.scalar(
        select(Connection).where(
            Connection.user_id == user_id,
            Connection.from_person_id == from_person_id,
            Connection.to_person_id == to_person_id,
            Connection.relation_type == relation_type,
        )
    )
    if existing is not None:
        return existing
    connection = Connection(
        user_id=user_id,
        from_person_id=from_person_id,
        to_person_id=to_person_id,
        relation_type=relation_type,
        note=note,
        source_message_id=source_message_id,
    )
    db.add(connection)
    db.flush()
    return connection
```

- [ ] **Step 6: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_services.py -v`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/companies.py backend/app/services/resolver.py backend/app/services/connections.py backend/tests/test_services.py
git commit -m "feat: add resolver, company, and connection service helpers with tests"
```

---

## Task 3: Relationship extraction schema and prompt

**Files:**
- Modify: `backend/app/schemas/extraction.py`
- Modify: `backend/app/llm/gemini.py`

- [ ] **Step 1: Update `backend/app/schemas/extraction.py` to add relationships**

Replace the file with:
```python
from typing import Optional

from pydantic import BaseModel


class ExtractedCompany(BaseModel):
    name: str


class ExtractedPerson(BaseModel):
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None


class ExtractedRelationship(BaseModel):
    from_person: str
    to_person: str
    relation_type: str = "knows"
    note: Optional[str] = None


class ExtractionResult(BaseModel):
    companies: list[ExtractedCompany] = []
    people: list[ExtractedPerson] = []
    relationships: list[ExtractedRelationship] = []
```

- [ ] **Step 2: Update the prompt in `backend/app/llm/gemini.py`**

Replace the `EXTRACTION_PROMPT` assignment with:
```python
EXTRACTION_PROMPT = (
    "You extract professional networking information from a message. "
    "Identify the people mentioned and the companies they are associated with. "
    "For each person, capture their name, their job title if stated, the company "
    "they are associated with if stated, and a short note about anything relevant "
    "they said or offered. List each distinct company by name. "
    "Also capture relationships between people: if one person knows, referred, or "
    "offered to introduce you to another person, record it as a relationship with "
    "from_person, to_person, and relation_type set to one of knows, referred, or "
    "can_intro. Only include information that is actually present in the message. "
    "Do not invent people, companies, or relationships.\n\nMessage:\n"
)
```

- [ ] **Step 3: Confirm the suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 35 passed (30 plus the 5 from Task 2). The existing GeminiClient tests still pass because `ExtractionResult()` simply gains an empty `relationships` list.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/extraction.py backend/app/llm/gemini.py
git commit -m "feat: extract person to person relationships"
```

---

## Task 4: Ingestion uses the Resolver and creates connections (TDD)

**Files:**
- Modify: `backend/app/services/ingest.py`
- Test: `backend/tests/test_relationships.py`

- [ ] **Step 1: Write the failing tests `backend/tests/test_relationships.py`**

```python
from sqlalchemy import select

from app.models.connection import Connection
from app.models.person import Person
from app.models.user import User
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractedRelationship,
    ExtractionResult,
)
from app.security import hash_password
from app.services.ingest import ingest_message
from tests.fakes import FakeLLMClient


def _make_user(db_session):
    user = User(email="u@example.com", hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_ingest_creates_connection_between_people(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Qualcomm")],
            people=[
                ExtractedPerson(name="Dipunj", company="Cloudflare"),
                ExtractedPerson(name="Rahul", company="Qualcomm"),
            ],
            relationships=[
                ExtractedRelationship(
                    from_person="Dipunj", to_person="Rahul", relation_type="knows"
                )
            ],
        )
    )

    ingest_message(db_session, user.id, "email", "raw", fake)

    people = {p.name: p for p in db_session.scalars(select(Person)).all()}
    connection = db_session.scalars(select(Connection)).one()
    assert connection.from_person_id == people["Dipunj"].id
    assert connection.to_person_id == people["Rahul"].id
    assert connection.relation_type == "knows"


def test_ingest_dedupes_people_across_pastes(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(people=[ExtractedPerson(name="Dipunj")])
    )
    ingest_message(db_session, user.id, "email", "first", fake)
    ingest_message(db_session, user.id, "email", "second", fake)

    dipunjs = db_session.scalars(
        select(Person).where(Person.name == "Dipunj")
    ).all()
    assert len(dipunjs) == 1
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relationships.py -v`
Expected: the connection test fails (no connections created) and the dedup test fails (two Dipunj rows), because ingestion does not yet use the resolver or create connections.

- [ ] **Step 3: Replace `backend/app/services/ingest.py`**

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm.base import LLMClient
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person
from app.services.companies import get_or_create_company
from app.services.connections import add_connection
from app.services.resolver import resolve_person


@dataclass
class IngestResult:
    message: Message
    companies: list[Company]
    people: list[Person]


def ingest_message(
    db: Session, user_id: str, source: str, text: str, llm: LLMClient
) -> IngestResult:
    message = Message(user_id=user_id, source=source, raw_text=text)
    db.add(message)
    db.flush()

    extraction = llm.extract_entities(text)

    companies_by_name: dict[str, Company] = {}
    for extracted in extraction.companies:
        companies_by_name[extracted.name] = get_or_create_company(
            db, user_id, extracted.name
        )

    people_by_id: dict[str, Person] = {}
    for extracted in extraction.people:
        person = resolve_person(db, user_id, extracted.name)
        company = None
        if extracted.company:
            company = companies_by_name.get(extracted.company)
            if company is None:
                company = get_or_create_company(db, user_id, extracted.company)
                companies_by_name[extracted.company] = company
        if extracted.title and not person.title:
            person.title = extracted.title
        if extracted.note and not person.note:
            person.note = extracted.note
        if company is not None and person.company_id is None:
            person.company_id = company.id
        if not person.source_message_id:
            person.source_message_id = message.id
        people_by_id[person.id] = person

    for relationship in extraction.relationships:
        from_person = resolve_person(db, user_id, relationship.from_person)
        to_person = resolve_person(db, user_id, relationship.to_person)
        for person in (from_person, to_person):
            if not person.source_message_id:
                person.source_message_id = message.id
            people_by_id[person.id] = person
        add_connection(
            db,
            user_id,
            from_person.id,
            to_person.id,
            relationship.relation_type or "knows",
            relationship.note,
            message.id,
        )

    message.processed = True
    db.commit()
    db.refresh(message)
    return IngestResult(
        message=message,
        companies=list(companies_by_name.values()),
        people=list(people_by_id.values()),
    )
```

- [ ] **Step 4: Run the relationship tests and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relationships.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 37 passed. The existing `tests/test_ingest.py` still passes: a newly resolved person gets its title, company, and `source_message_id` set exactly as before.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ingest.py backend/tests/test_relationships.py
git commit -m "feat: ingestion resolves people and records relationships"
```

---

## Task 5: Manual add with "known through" (TDD)

**Files:**
- Modify: `backend/app/schemas/people.py`
- Modify: `backend/app/services/people.py`
- Modify: `backend/app/routers/people.py`
- Test: `backend/tests/test_relationships.py`

- [ ] **Step 1: Add the failing test to `backend/tests/test_relationships.py`**

Append:
```python
def test_add_person_known_through_creates_connection(client):
    register = client.post(
        "/auth/register", json={"email": "k@example.com", "password": "hunter2"}
    )
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

    client.post("/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"})
    response = client.post(
        "/people",
        headers=headers,
        json={"name": "Rahul", "company": "Qualcomm", "known_through": "Dipunj"},
    )
    assert response.status_code == 201

    graph = client.get("/graph", headers=headers).json()
    labels_by_id = {n["id"]: n["label"] for n in graph["nodes"]}
    knows_edges = [
        (labels_by_id.get(e["source"]), labels_by_id.get(e["target"]))
        for e in graph["edges"]
        if e["label"] == "KNOWS"
    ]
    assert ("Dipunj", "Rahul") in knows_edges
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relationships.py::test_add_person_known_through_creates_connection -v`
Expected: fails because `known_through` is not accepted or no connection is created.

- [ ] **Step 3: Update `backend/app/schemas/people.py`**

```python
from typing import Optional

from pydantic import BaseModel


class PersonCreate(BaseModel):
    name: str
    company: Optional[str] = None
    known_through: Optional[str] = None
```

- [ ] **Step 4: Replace `backend/app/services/people.py`**

```python
from typing import Optional

from sqlalchemy.orm import Session

from app.models.person import Person
from app.services.companies import get_or_create_company
from app.services.connections import add_connection
from app.services.resolver import resolve_person


def add_person(
    db: Session,
    user_id: str,
    name: str,
    company_name: Optional[str],
    known_through: Optional[str] = None,
) -> Person:
    person = resolve_person(db, user_id, name)
    if company_name:
        company = get_or_create_company(db, user_id, company_name)
        if person.company_id is None:
            person.company_id = company.id
    if known_through:
        introducer = resolve_person(db, user_id, known_through)
        add_connection(db, user_id, introducer.id, person.id, "knows")
    db.commit()
    db.refresh(person)
    return person
```

- [ ] **Step 5: Update the call in `backend/app/routers/people.py`**

Change the `add_person` call to pass `known_through`. The handler body becomes:
```python
    person = add_person(
        db, current_user.id, payload.name, payload.company, payload.known_through
    )
```
Leave the rest of the file unchanged.

- [ ] **Step 6: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relationships.py -v`
Expected: 3 passed.

- [ ] **Step 7: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 38 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/people.py backend/app/services/people.py backend/app/routers/people.py backend/tests/test_relationships.py
git commit -m "feat: support adding a person known through an existing contact"
```

---

## Task 6: Graph view adds the You node and relationship edges (TDD)

**Files:**
- Modify: `backend/app/services/graph_view.py`
- Modify: `backend/tests/test_graph_view.py`
- Modify: `backend/tests/test_graph.py`
- Modify: `backend/tests/test_people.py`

This task intentionally changes graph output (adds a `You` node and relationship edges), so three existing tests are updated to match the new, intended behavior.

- [ ] **Step 1: Replace `backend/app/services/graph_view.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.connection import Connection
from app.models.person import Person
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse

YOU_NODE_ID = "you"


def build_graph(db: Session, user_id: str) -> GraphResponse:
    companies = db.scalars(
        select(Company).where(Company.user_id == user_id)
    ).all()
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()
    connections = db.scalars(
        select(Connection).where(Connection.user_id == user_id)
    ).all()

    introduced = {c.to_person_id for c in connections}

    nodes: list[GraphNode] = [
        GraphNode(id=YOU_NODE_ID, label="You", type="you")
    ]
    edges: list[GraphEdge] = []

    for company in companies:
        nodes.append(
            GraphNode(id=f"company:{company.id}", label=company.name, type="company")
        )

    for person in people:
        nodes.append(
            GraphNode(id=f"person:{person.id}", label=person.name, type="person")
        )
        if person.company_id is not None:
            edges.append(
                GraphEdge(
                    source=f"person:{person.id}",
                    target=f"company:{person.company_id}",
                    label="WORKS_AT",
                )
            )
        if person.id not in introduced:
            edges.append(
                GraphEdge(
                    source=YOU_NODE_ID,
                    target=f"person:{person.id}",
                    label="KNOWS",
                )
            )

    for connection in connections:
        edges.append(
            GraphEdge(
                source=f"person:{connection.from_person_id}",
                target=f"person:{connection.to_person_id}",
                label=connection.relation_type.upper(),
            )
        )

    return GraphResponse(nodes=nodes, edges=edges)
```

- [ ] **Step 2: Update `backend/tests/test_graph_view.py`**

The graph now always contains a `You` node and links first-degree people to it. Replace the two assertions that expected an empty graph or no edges:

In `test_build_graph_excludes_other_users`, replace:
```python
    assert graph.nodes == []
    assert graph.edges == []
```
with:
```python
    assert [n for n in graph.nodes if n.type != "you"] == []
    assert graph.edges == []
```

In `test_build_graph_person_without_company_has_no_edge`, replace:
```python
    assert any(n.label == "Solo" and n.type == "person" for n in graph.nodes)
    assert graph.edges == []
```
with:
```python
    assert any(n.label == "Solo" and n.type == "person" for n in graph.nodes)
    assert not any(e.label == "WORKS_AT" for e in graph.edges)
    assert any(
        e.source == "you" and e.label == "KNOWS" for e in graph.edges
    )
```

- [ ] **Step 3: Update `backend/tests/test_graph.py`**

In `test_graph_empty_for_new_user`, replace:
```python
    assert response.json() == {"nodes": [], "edges": []}
```
with:
```python
    body = response.json()
    assert body["nodes"] == [{"id": "you", "label": "You", "type": "you"}]
    assert body["edges"] == []
```

- [ ] **Step 4: Update `backend/tests/test_people.py`**

In `test_add_person_without_company`, replace:
```python
    graph = client.get("/graph", headers=headers).json()
    assert any(n["label"] == "Solo" for n in graph["nodes"])
    assert graph["edges"] == []
```
with:
```python
    graph = client.get("/graph", headers=headers).json()
    assert any(n["label"] == "Solo" for n in graph["nodes"])
    assert not any(e["label"] == "WORKS_AT" for e in graph["edges"])
    assert any(
        e["source"] == "you" and e["label"] == "KNOWS" for e in graph["edges"]
    )
```

- [ ] **Step 5: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 38 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/graph_view.py backend/tests/test_graph_view.py backend/tests/test_graph.py backend/tests/test_people.py
git commit -m "feat: graph shows a You node and person to person edges"
```

---

## Task 7: Frontend, known-through input and edge styling

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add a "known through" input to the toolbar**

In `frontend/index.html`, find the toolbar block that contains the `pcompany` input and the Add button:
```html
      <input id="pcompany" placeholder="company (optional)" onkeydown="if(event.key==='Enter')addPerson()" />
      <button onclick="addPerson()">Add</button>
```
Replace it with:
```html
      <input id="pcompany" placeholder="company (optional)" onkeydown="if(event.key==='Enter')addPerson()" />
      <input id="pknown" placeholder="known through (optional)" onkeydown="if(event.key==='Enter')addPerson()" />
      <button onclick="addPerson()">Add</button>
```

- [ ] **Step 2: Send `known_through` in `addPerson`**

In the `addPerson` function, replace:
```javascript
      const name = document.getElementById("pname").value.trim();
      const company = document.getElementById("pcompany").value.trim();
      const status = document.getElementById("addStatus");
      if (!name) { status.textContent = "Enter a name."; return; }
      status.textContent = "Adding...";
      try {
        await api("/people", { method: "POST", body: JSON.stringify({ name, company: company || null }) });
        document.getElementById("pname").value = "";
        document.getElementById("pcompany").value = "";
        status.textContent = "";
        loadGraph();
      } catch (e) { status.textContent = "Failed to add."; }
```
with:
```javascript
      const name = document.getElementById("pname").value.trim();
      const company = document.getElementById("pcompany").value.trim();
      const knownThrough = document.getElementById("pknown").value.trim();
      const status = document.getElementById("addStatus");
      if (!name) { status.textContent = "Enter a name."; return; }
      status.textContent = "Adding...";
      try {
        await api("/people", { method: "POST", body: JSON.stringify({
          name: name,
          company: company || null,
          known_through: knownThrough || null,
        }) });
        document.getElementById("pname").value = "";
        document.getElementById("pcompany").value = "";
        document.getElementById("pknown").value = "";
        status.textContent = "";
        loadGraph();
      } catch (e) { status.textContent = e.message || "Failed to add."; }
```

- [ ] **Step 3: Style the You node and relationship edges**

In `toVisNode`, replace the function body with one that handles the `you` type:
```javascript
    function toVisNode(n) {
      if (n.type === "you") {
        return {
          id: n.id,
          label: n.label,
          shape: "dot",
          size: 28,
          color: { background: "#f59e0b", border: "#fcd34d",
                   highlight: { background: "#fbbf24", border: "#fde68a" } },
        };
      }
      const isCompany = n.type === "company";
      return {
        id: n.id,
        label: n.label,
        shape: isCompany ? "hexagon" : "dot",
        size: isCompany ? 24 : 16,
        color: isCompany
          ? { background: "#6366f1", border: "#a5b4fc", highlight: { background: "#818cf8", border: "#c7d2fe" } }
          : { background: "#10b981", border: "#6ee7b7", highlight: { background: "#34d399", border: "#a7f3d0" } },
      };
    }
```

In `toVisEdge`, color relationship edges differently from `WORKS_AT`:
```javascript
    function toVisEdge(e) {
      const isWork = e.label === "WORKS_AT";
      return {
        id: edgeId(e),
        from: e.source,
        to: e.target,
        label: e.label,
        color: { color: isWork ? "#3b4862" : "#0e7490",
                 highlight: "#94a3b8", hover: "#64748b" },
        dashes: isWork ? false : [6, 4],
      };
    }
```

- [ ] **Step 4: Confirm the suite still passes (no backend change here)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 38 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: known-through input and relationship edge styling in the map"
```

---

## Task 8: End-to-end verification (local, no Docker)

**Files:** none (verification only).

- [ ] **Step 1: Start the app on a fresh SQLite database in the background**

From the `backend` directory (PowerShell), run in the background:
```
$env:DATABASE_URL = "sqlite:///./kith_p3.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

- [ ] **Step 2: Register, add Dipunj, add Rahul known through Dipunj, read the graph**

```
$reg = Invoke-RestMethod -Uri http://localhost:8000/auth/register -Method Post -ContentType application/json -Body '{"email":"p3@example.com","password":"hunter2"}'
$h = @{ Authorization = "Bearer " + $reg.access_token }
Invoke-RestMethod -Uri http://localhost:8000/people -Method Post -ContentType application/json -Headers $h -Body '{"name":"Dipunj","company":"Cloudflare"}' | Out-Null
Invoke-RestMethod -Uri http://localhost:8000/people -Method Post -ContentType application/json -Headers $h -Body '{"name":"Rahul","company":"Qualcomm","known_through":"Dipunj"}' | Out-Null
Invoke-RestMethod -Uri http://localhost:8000/graph -Method Get -Headers $h | ConvertTo-Json -Depth 6
```
Expected: nodes include `You`, Dipunj, Rahul, Cloudflare, Qualcomm. Edges include `You KNOWS Dipunj`, `Dipunj WORKS_AT Cloudflare`, `Dipunj KNOWS Rahul`, `Rahul WORKS_AT Qualcomm`, and NO `You KNOWS Rahul` (Rahul is second-degree).

- [ ] **Step 3: Stop the background server**

Stop the background uvicorn process.

- [ ] **Step 4: Manual browser check**

Tell the user to run the app (README command), open http://localhost:8000, add a person "known through" someone, and confirm the new contact links to both the introducer and their company in the floating graph.

- [ ] **Step 5: Commit any fixes**

If verification required changes, commit them with a clear message. The `kith_p3.db` file is ignored by `.gitignore` (`*.db`).

---

## Self-Review

**Spec coverage:**
- `connections` table: Task 1. Resolver: Task 2 and used in Tasks 4 and 5. `known_through` manual add: Task 5. Relationship extraction: Tasks 3 and 4. `You` node plus relationship edges in `/graph`: Task 6. Frontend known-through and edge styling: Task 7. Hermetic tests throughout. Deferred items (Neo4j, warm-path query) are correctly absent.

**Type consistency:** `resolve_person(db, user_id, name) -> Person`, `get_or_create_company(db, user_id, name) -> Company`, and `add_connection(db, user_id, from_person_id, to_person_id, relation_type, note, source_message_id) -> Connection` are defined in Task 2 and called with matching signatures in Tasks 4 and 5. `ExtractedRelationship(from_person, to_person, relation_type, note)` defined in Task 3 is consumed in Task 4. `GraphNode`/`GraphEdge` fields are unchanged; the new `you` node type and `KNOWS`/`REFERRED`/`CAN_INTRO` edge labels are handled in the frontend (Task 7). `PersonCreate.known_through` (Task 5) matches the router call and the frontend body (Task 7).

**Placeholder scan:** No TBDs. Every code step is complete; every test step has real assertions and exact expected counts (30, 35, 37, 38).

**Behavior-change note:** Task 6 updates three existing tests on purpose because the graph output intentionally gains a `You` node and first-degree `KNOWS` edges. These are the only existing tests touched, and the changes are spelled out exactly.

**Known pragmatic choices:** dedup is by normalized exact name (semantic dedup via embeddings is a later phase); connections are deduped by (from, to, relation_type); the warm-path query and Neo4j are the next phase; the frontend remains a single static file verified manually.
