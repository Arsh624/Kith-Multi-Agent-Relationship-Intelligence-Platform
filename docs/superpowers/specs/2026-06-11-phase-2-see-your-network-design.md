# Kith Phase 2: See Your Network

**Design spec** · 2026-06-11

## Purpose

Give Kith its first visual payoff: open a page, log in, paste a contact, and watch
your network appear as an interactive graph that grows with each paste. This turns the
Phase 1 backend (which already extracts and stores people and companies) into something
you can actually look at and use.

## Scope

### In scope (Phase 2)
- A `GET /graph` endpoint (JWT-protected) that returns the signed-in user's network as
  nodes and edges, built from the existing Postgres data (people, companies, and the
  WORKS_AT link via `Person.company_id`).
- A single self-contained HTML page (no build step, no framework) with three parts:
  a login box, a paste box, and a live network map rendered with Cytoscape.js (loaded
  from a CDN). Served by FastAPI itself, so the page and API share an origin and there
  is no CORS configuration.
- A documented zero-Docker local run: the app runs against a local SQLite file, so the
  user can start it with one command and open `http://localhost:8000`.

### Explicitly deferred to the next phase
- Neo4j and the graph database layer.
- Person-to-person relationship extraction (knows / referred / can_intro).
- The Resolver (person deduplication).
- The "warm intro path" graph query.

These all become justified once person-to-person edges exist, so they are added as a
focused follow-up immediately after this phase ships. Phase 2 deliberately uses only
Postgres data a relational query handles well.

## Success criteria
- With the app running, a user can register/log in on the page, paste a message, and see
  new company and person nodes appear in the map, connected by WORKS_AT edges.
- `GET /graph` returns correct nodes and edges scoped to the signed-in user, and is
  covered by hermetic tests (no real Gemini calls; SQLite database).
- The whole thing runs locally with no Docker and no Postgres.

## Architecture

### Backend: `GET /graph`
- JWT-protected (reuses `get_current_user`).
- Reads the user's `companies` and `people` from Postgres.
- Returns a `GraphResponse`:
  - `nodes`: list of `{ id, label, type }` where `type` is `"company"` or `"person"`.
    Node ids are namespaced (for example `company:<uuid>`, `person:<uuid>`) so company
    and person ids never collide in the graph.
  - `edges`: list of `{ source, target, label }`. For each person with a `company_id`,
    one edge from the person node to the company node labeled `WORKS_AT`.
- Lives in a thin router (`app/routers/graph.py`) backed by a small read service
  (`app/services/graph_view.py`) so the query logic is testable on its own.

### Frontend: one static page
- `frontend/index.html`: plain HTML, CSS, and vanilla JS. Cytoscape.js from a CDN.
- Three sections: login (calls `POST /auth/login`, stores the JWT in `localStorage`),
  paste (calls `POST /paste` with the bearer token), and the map (calls `GET /graph`
  and renders nodes/edges, refreshing after each successful paste).
- Served by FastAPI via `StaticFiles` mounted so the page is reachable at the app root,
  keeping it same-origin with the API.

### Local run (zero Docker)
- The app reads `DATABASE_URL`; pointing it at `sqlite:///./kith_local.db` runs the full
  stack on a local file with no external services. Documented in the README with the
  exact command. Gemini still needs the key in `.env` for real pastes (already present).

## Data flow
1. User logs in on the page; the JWT is stored client-side.
2. User pastes a message; the page calls `POST /paste`; Phase 1 ingestion extracts and
   stores people and companies in Postgres (or SQLite locally).
3. The page calls `GET /graph`; the backend reads the user's people and companies and
   returns nodes and edges.
4. Cytoscape renders the network; pasting again repeats from step 2 and the map grows.

## Testing
- `GET /graph`: hermetic tests using the existing SQLite fixture and a FakeLLMClient
  injected via dependency override. Register a user, paste (with a canned extraction),
  then assert the graph response contains the expected company and person nodes and a
  WORKS_AT edge between them. Also assert the endpoint requires auth.
- The HTML page is verified manually by the user running the app and using it (it has no
  build step and no logic worth unit testing in isolation for this phase).

## Files (planned)
```
backend/app/schemas/graph.py        GraphNode, GraphEdge, GraphResponse
backend/app/services/graph_view.py  build_graph(db, user_id) -> GraphResponse
backend/app/routers/graph.py        GET /graph
backend/app/main.py                 include graph router, mount static frontend
frontend/index.html                 login + paste + Cytoscape map
backend/tests/test_graph.py         hermetic tests for /graph
README.md                           zero-Docker local run instructions
```
