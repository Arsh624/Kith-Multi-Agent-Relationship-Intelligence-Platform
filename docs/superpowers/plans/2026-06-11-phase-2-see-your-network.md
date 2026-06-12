# Kith Phase 2: See Your Network Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a JWT-protected `GET /graph` endpoint that returns the user's people and companies as a node/edge graph, plus a single self-contained HTML page (Cytoscape.js from a CDN) served by FastAPI, so the user can log in, paste a message, and watch their network render and grow.

**Architecture:** `GET /graph` reads the signed-in user's companies and people from Postgres (the data Phase 1 already stores) and returns namespaced nodes plus WORKS_AT edges, via a small testable read service. A static `frontend/index.html` is mounted at the app root with `StaticFiles`, keeping it same-origin with the API (no CORS). The whole app runs locally against SQLite, so no Docker or Postgres is needed to see it work.

**Tech Stack:** FastAPI StaticFiles, SQLAlchemy 2.0, Cytoscape.js (browser, via CDN), pytest. Builds on Phase 0 and Phase 1. No new Python dependencies.

---

## Context for the implementer

Phase 0 and Phase 1 are complete (18 passing tests). Relevant existing pieces:
- `app/models/company.py` (`Company`: id, user_id, name), `app/models/person.py` (`Person`: id, user_id, name, title, note, company_id, source_message_id).
- `app/deps.py` has `get_current_user` (JWT) and `get_llm_client`.
- `app/routers/paste.py` exposes `POST /paste`; `app/services/ingest.py` persists people/companies.
- `app/main.py` currently includes the health, auth, and paste routers and registers all models.
- `tests/conftest.py` provides a `client` fixture (TestClient, hermetic SQLite) and a `db_session` fixture; `tests/fakes.py` has `FakeLLMClient`.
- Run tests from the `backend` directory: `.\.venv\Scripts\python.exe -m pytest -v`.

No em dashes or en dashes anywhere (code, comments, commit messages, HTML text).

## File Structure (Phase 2 additions)

```
backend/app/schemas/graph.py         NEW: GraphNode, GraphEdge, GraphResponse
backend/app/services/graph_view.py   NEW: build_graph(db, user_id) -> GraphResponse
backend/app/routers/graph.py         NEW: GET /graph
backend/app/main.py                  MODIFY: include graph router (Task 2), mount static frontend (Task 3)
frontend/index.html                  NEW: login + paste + Cytoscape map (single file)
backend/tests/test_graph_view.py     NEW: service unit tests
backend/tests/test_graph.py          NEW: endpoint tests
README.md                            MODIFY: zero-Docker local run section
```

---

## Task 1: Graph schemas and read service (TDD)

**Files:**
- Create: `backend/app/schemas/graph.py`
- Create: `backend/app/services/graph_view.py`
- Test: `backend/tests/test_graph_view.py`

- [ ] **Step 1: Create `backend/app/schemas/graph.py`**

```python
from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
```

- [ ] **Step 2: Write the failing test `backend/tests/test_graph_view.py`**

```python
from app.models.company import Company
from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.services.graph_view import build_graph


def _make_user(db_session, email="u@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_build_graph_returns_company_person_and_edge(db_session):
    user = _make_user(db_session)
    company = Company(user_id=user.id, name="Stripe")
    db_session.add(company)
    db_session.flush()
    person = Person(user_id=user.id, name="Priya", company_id=company.id)
    db_session.add(person)
    db_session.commit()

    graph = build_graph(db_session, user.id)

    node_types = {n.label: n.type for n in graph.nodes}
    assert node_types["Stripe"] == "company"
    assert node_types["Priya"] == "person"
    assert any(
        e.label == "WORKS_AT"
        and e.source == f"person:{person.id}"
        and e.target == f"company:{company.id}"
        for e in graph.edges
    )


def test_build_graph_excludes_other_users(db_session):
    owner = _make_user(db_session, email="owner@example.com")
    other = _make_user(db_session, email="other@example.com")
    company = Company(user_id=owner.id, name="Stripe")
    db_session.add(company)
    db_session.commit()

    graph = build_graph(db_session, other.id)

    assert graph.nodes == []
    assert graph.edges == []


def test_build_graph_person_without_company_has_no_edge(db_session):
    user = _make_user(db_session)
    person = Person(user_id=user.id, name="Solo")
    db_session.add(person)
    db_session.commit()

    graph = build_graph(db_session, user.id)

    assert any(n.label == "Solo" and n.type == "person" for n in graph.nodes)
    assert graph.edges == []
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_graph_view.py -v`
Expected: import error, `app.services.graph_view` does not exist yet.

- [ ] **Step 4: Create `backend/app/services/graph_view.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.person import Person
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


def build_graph(db: Session, user_id: str) -> GraphResponse:
    companies = db.scalars(
        select(Company).where(Company.user_id == user_id)
    ).all()
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()

    nodes: list[GraphNode] = []
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

    return GraphResponse(nodes=nodes, edges=edges)
```

- [ ] **Step 5: Run the test and confirm it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_graph_view.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/graph.py backend/app/services/graph_view.py backend/tests/test_graph_view.py
git commit -m "feat: add graph schemas and build_graph read service"
```

---

## Task 2: The /graph endpoint (TDD)

**Files:**
- Create: `backend/app/routers/graph.py`
- Modify: `backend/app/main.py` (include the graph router)
- Test: `backend/tests/test_graph.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_graph.py`**

```python
from app.deps import get_llm_client
from app.main import app
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractionResult,
)
from tests.fakes import FakeLLMClient


def _register(client, email="u@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return response.json()["access_token"]


def test_graph_returns_nodes_and_edges_after_paste(client):
    token = _register(client)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(
                    name="Priya Sharma", title="PM", company="Stripe", note="x"
                )
            ],
        )
    )
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        client.post(
            "/paste",
            headers={"Authorization": f"Bearer {token}"},
            json={"source": "email", "text": "Priya is a PM at Stripe."},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    response = client.get(
        "/graph", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()

    labels = {n["label"]: n["type"] for n in body["nodes"]}
    assert labels.get("Stripe") == "company"
    assert labels.get("Priya Sharma") == "person"

    person_id = next(
        n["id"] for n in body["nodes"] if n["label"] == "Priya Sharma"
    )
    company_id = next(
        n["id"] for n in body["nodes"] if n["label"] == "Stripe"
    )
    assert any(
        e["source"] == person_id
        and e["target"] == company_id
        and e["label"] == "WORKS_AT"
        for e in body["edges"]
    )


def test_graph_requires_auth(client):
    response = client.get("/graph")
    assert response.status_code in (401, 403)


def test_graph_empty_for_new_user(client):
    token = _register(client)
    response = client.get(
        "/graph", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"nodes": [], "edges": []}
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_graph.py -v`
Expected: the `/graph` requests return 404 (route not wired), so the first and third tests fail. Record the output.

- [ ] **Step 3: Create `backend/app/routers/graph.py`**

```python
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
```

- [ ] **Step 4: Wire the graph router into `backend/app/main.py`**

Change the routers import to include `graph`, and add an include line. The file should read:
```python
from fastapi import FastAPI

from app.database import Base, engine
import app.models  # noqa: F401  registers all model tables
from app.routers import auth, graph, health, paste

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(paste.router)
app.include_router(graph.router)
```

- [ ] **Step 5: Run the graph tests and confirm they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_graph.py -v`
Expected: 3 passed.

- [ ] **Step 6: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 24 passed (18 from before plus 3 graph_view plus 3 graph).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/graph.py backend/app/main.py backend/tests/test_graph.py
git commit -m "feat: add JWT-protected /graph endpoint with tests"
```

---

## Task 3: The frontend page and static mount

**Files:**
- Create: `frontend/index.html`
- Modify: `backend/app/main.py` (mount static files)
- Modify: `README.md` (local run instructions)

- [ ] **Step 1: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kith</title>
  <script src="https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; color: #1a1a1a; }
    header { padding: 12px 20px; background: #0f172a; color: #fff;
             display: flex; justify-content: space-between; align-items: center; }
    header h1 { font-size: 18px; margin: 0; }
    #auth, #app { padding: 20px; }
    #app { display: none; }
    input, textarea, button { font: inherit; padding: 8px; margin: 4px 0; }
    input, textarea { width: 100%; box-sizing: border-box;
                      border: 1px solid #cbd5e1; border-radius: 6px; }
    button { background: #2563eb; color: #fff; border: none;
             border-radius: 6px; cursor: pointer; padding: 8px 14px; }
    button.secondary { background: #64748b; }
    .row { display: flex; gap: 20px; align-items: flex-start; }
    .panel { flex: 1; }
    #cy { height: 70vh; border: 1px solid #e2e8f0; border-radius: 8px;
          background: #f8fafc; }
    .muted { color: #64748b; font-size: 13px; }
    .error { color: #dc2626; font-size: 13px; }
  </style>
</head>
<body>
  <header>
    <h1>Kith</h1>
    <button id="logout" class="secondary" style="display:none" onclick="logout()">Log out</button>
  </header>

  <div id="auth">
    <h2>Sign in</h2>
    <input id="email" type="email" placeholder="email" />
    <input id="password" type="password" placeholder="password" />
    <div>
      <button onclick="login()">Log in</button>
      <button class="secondary" onclick="register()">Register</button>
    </div>
    <p id="authError" class="error"></p>
  </div>

  <div id="app">
    <div class="row">
      <div class="panel">
        <h2>Paste a message</h2>
        <input id="source" placeholder="source (email, linkedin, ...)" value="email" />
        <textarea id="text" rows="8" placeholder="Paste an email or message here..."></textarea>
        <button onclick="paste()">Extract</button>
        <p id="pasteStatus" class="muted"></p>
      </div>
      <div class="panel">
        <h2>Your network</h2>
        <div id="cy"></div>
      </div>
    </div>
  </div>

  <script>
    function token() { return localStorage.getItem("kith_token"); }
    function setToken(t) { localStorage.setItem("kith_token", t); }
    function clearToken() { localStorage.removeItem("kith_token"); }

    async function api(path, options) {
      options = options || {};
      options.headers = Object.assign(
        { "Content-Type": "application/json" }, options.headers || {}
      );
      const t = token();
      if (t) options.headers["Authorization"] = "Bearer " + t;
      const res = await fetch(path, options);
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || String(res.status));
      }
      return res.json();
    }

    async function register() { await auth("/auth/register"); }
    async function login() { await auth("/auth/login"); }

    async function auth(path) {
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;
      document.getElementById("authError").textContent = "";
      try {
        const data = await api(path, {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        setToken(data.access_token);
        showApp();
      } catch (e) {
        document.getElementById("authError").textContent =
          "Could not authenticate. Check your details.";
      }
    }

    function logout() {
      clearToken();
      document.getElementById("app").style.display = "none";
      document.getElementById("auth").style.display = "block";
      document.getElementById("logout").style.display = "none";
    }

    function showApp() {
      document.getElementById("auth").style.display = "none";
      document.getElementById("app").style.display = "block";
      document.getElementById("logout").style.display = "inline-block";
      loadGraph();
    }

    async function paste() {
      const source = document.getElementById("source").value;
      const text = document.getElementById("text").value;
      const status = document.getElementById("pasteStatus");
      status.textContent = "Extracting...";
      try {
        const result = await api("/paste", {
          method: "POST",
          body: JSON.stringify({ source, text }),
        });
        status.textContent =
          "Added " + result.people.length + " people and " +
          result.companies.length + " companies.";
        document.getElementById("text").value = "";
        loadGraph();
      } catch (e) {
        status.textContent = "Extraction failed.";
      }
    }

    let cy;
    async function loadGraph() {
      const graph = await api("/graph");
      const elements = [];
      for (const n of graph.nodes) {
        elements.push({ data: { id: n.id, label: n.label, type: n.type } });
      }
      for (const e of graph.edges) {
        elements.push({ data: { source: e.source, target: e.target, label: e.label } });
      }
      if (!cy) {
        cy = cytoscape({
          container: document.getElementById("cy"),
          elements: elements,
          style: [
            { selector: "node", style: {
              "label": "data(label)", "font-size": "11px",
              "text-valign": "center", "color": "#fff",
              "text-outline-width": 2, "text-outline-color": "#334155" } },
            { selector: 'node[type="company"]', style: {
              "background-color": "#2563eb", "shape": "round-rectangle",
              "width": 70, "height": 30 } },
            { selector: 'node[type="person"]', style: {
              "background-color": "#10b981" } },
            { selector: "edge", style: {
              "label": "data(label)", "font-size": "9px", "color": "#64748b",
              "width": 1, "line-color": "#cbd5e1",
              "target-arrow-color": "#cbd5e1", "target-arrow-shape": "triangle",
              "curve-style": "bezier" } }
          ],
          layout: { name: "cose", animate: false }
        });
      } else {
        cy.elements().remove();
        cy.add(elements);
        cy.layout({ name: "cose", animate: false }).run();
      }
    }

    if (token()) { showApp(); }
  </script>
</body>
</html>
```

- [ ] **Step 2: Mount the frontend in `backend/app/main.py`**

Add the `Path` and `StaticFiles` imports and mount the `frontend` directory at the app root, AFTER all routers are included. The full file should read:
```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
import app.models  # noqa: F401  registers all model tables
from app.routers import auth, graph, health, paste

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(paste.router)
app.include_router(graph.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
```

Note: the static mount is added last on purpose. The API routes are registered before it, so they take precedence; the mount only serves unmatched paths such as `/` and `/index.html`.

- [ ] **Step 3: Confirm the whole suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 24 passed. The static mount must not break existing routes. If `StaticFiles` raises because the directory is missing, confirm `frontend/index.html` was created in Step 1 (the directory must exist at import time).

- [ ] **Step 4: Add a local-run section to `README.md`**

Append this section to the end of `README.md`:
```markdown
## Run it locally and see your network (no Docker)

From the `backend` directory, run the app against a local SQLite file:

PowerShell:

    $env:DATABASE_URL = "sqlite:///./kith_local.db"
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Then open http://localhost:8000 in your browser. Register, paste an email or
message, and watch the network map fill in. The Gemini key in `backend/.env`
powers the extraction.
```

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html backend/app/main.py README.md
git commit -m "feat: add single-file network map page served by FastAPI"
```

---

## Task 4: End-to-end verification (local, no Docker)

**Files:** none (verification only).

This proves the full loop works against a real SQLite database and the real Gemini key.

- [ ] **Step 1: Start the app against SQLite in the background**

From the `backend` directory (PowerShell), set the env var and start uvicorn in the background:
```
$env:DATABASE_URL = "sqlite:///./kith_e2e.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
Run this with the background option so it keeps running. Give it a few seconds to start.

- [ ] **Step 2: Confirm the page is served**

Run: `curl http://localhost:8000/ -UseBasicParsing | Select-Object -ExpandProperty Content | Select-String "Kith"`
Expected: the HTML contains "Kith" (the page title), proving the static mount serves `index.html`.

- [ ] **Step 3: Register, paste a real message, and read the graph**

Run these in PowerShell (they exercise the real endpoints and real Gemini):
```
$body = '{"email":"e2e@example.com","password":"hunter2"}'
$reg = Invoke-RestMethod -Uri http://localhost:8000/auth/register -Method Post -ContentType application/json -Body $body
$headers = @{ Authorization = "Bearer " + $reg.access_token }
$paste = '{"source":"email","text":"Hi, I am a PM at Stripe. My friend Ravi leads recruiting at Notion, ping me to connect."}'
Invoke-RestMethod -Uri http://localhost:8000/paste -Method Post -ContentType application/json -Headers $headers -Body $paste
Invoke-RestMethod -Uri http://localhost:8000/graph -Method Get -Headers $headers | ConvertTo-Json -Depth 5
```
Expected: the `/graph` response lists company nodes (for example Stripe and Notion) and person nodes, with WORKS_AT edges. The exact entities depend on the live model, but there should be at least one company node and the response should have the `nodes` and `edges` shape.

- [ ] **Step 4: Stop the background server**

Stop the background uvicorn process.

- [ ] **Step 5: Manual browser check (the actual payoff)**

Tell the user to run the local-run command from the README, open http://localhost:8000, register, paste a message, and confirm the map renders and grows. This visual confirmation is the real acceptance test for this phase.

- [ ] **Step 6: Remove the throwaway local databases**

The files `backend/kith_e2e.db` and `backend/kith_local.db` are local SQLite scratch files and are already ignored by `.gitignore` (`*.db`). No commit needed. If any other changes were made during verification, commit them with a clear message.

---

## Self-Review

**Spec coverage:**
- `GET /graph` from Postgres data, nodes plus WORKS_AT edges, namespaced ids: Task 1 (service) and Task 2 (endpoint).
- JWT protection: Task 2 (reuses `get_current_user`), asserted by `test_graph_requires_auth`.
- Single self-contained HTML page (login, paste, Cytoscape map) served same-origin via StaticFiles: Task 3.
- Zero-Docker local run on SQLite: Task 3 (README) and Task 4 (verification).
- Hermetic tests for `/graph` (SQLite, FakeLLMClient): Task 2.
- Deferred items (Neo4j, relationship extraction, Resolver, intro paths) are correctly absent.

**Type consistency:** `build_graph(db, user_id) -> GraphResponse` is defined in Task 1 and called identically in Task 2's router. `GraphNode(id, label, type)`, `GraphEdge(source, target, label)`, and `GraphResponse(nodes, edges)` field names match across the schema, the service, the tests, and the frontend's `n.label`/`n.type`/`e.source`/`e.target`/`e.label` usage. Node id namespacing (`company:<id>`, `person:<id>`) is consistent between the service and the endpoint test assertions.

**Placeholder scan:** No TBDs. Every code step is complete. Test steps show real assertions and exact commands with expected counts (24 passing after Task 2).

**Known pragmatic choices:** the map is read from Postgres (Neo4j arrives next phase); the page is a single static file with no build step or automated UI test (verified manually in Task 4); local runs use SQLite while production config still targets Postgres.
