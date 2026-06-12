# Kith Phase 4: Neo4j Warm Paths

**Design spec** · 2026-06-12

## Purpose

Make Neo4j earn its place: mirror the relationship graph into Neo4j and answer the
question a relational database is bad at, "who can get me into a given company?" by
walking multi-hop paths from You through your contacts to someone who works there
(for example You to Dipunj to Rahul to Qualcomm).

## Scope

### In scope (Phase 4)
- A `GraphStore` interface with a real `Neo4jGraphStore` (official `neo4j` driver, Aura)
  and an in-memory `FakeGraphStore` for hermetic tests, injected through a
  `get_graph_store` dependency (same pattern as `LLMClient`).
- `POST /graph/sync`: read the signed-in user's people, companies, and connections from
  Postgres and rebuild that user's subgraph in Neo4j (Postgres stays the source of truth;
  Neo4j is a derived, queryable mirror).
- `GET /intro-paths?company=<name>`: return shortest warm paths from You to people who
  work at the named company, each path as an ordered list of names.
- Frontend: a "who can get me into [company]?" box that shows the path(s), and a best
  effort auto-sync after adds and pastes so the mirror stays current. A manual "Sync"
  action is also available.
- A smoke test that runs against the real Aura instance.

### Explicitly deferred
- Realtime write-through to Neo4j on every mutation (we rebuild via sync instead, so a
  Neo4j outage never breaks adds or pastes).
- Visualizing paths inside the floating graph (Phase 4 lists them as text first).
- Semantic person dedup (Qdrant) and the observability/evals phase.

## Success criteria
- After adding Dipunj (Cloudflare) and Rahul (Qualcomm, known through Dipunj) and syncing,
  `GET /intro-paths?company=Qualcomm` returns a path like `["You", "Dipunj", "Rahul",
  "Qualcomm"]`.
- A company with no path returns an empty list.
- The whole test suite stays hermetic (FakeGraphStore), needing no Neo4j to run.
- The real Aura connection is verified by a smoke script.

## Architecture

### GraphStore interface (`app/graph/base.py`)
```
class GraphStore(ABC):
    def sync_user_graph(self, user_id, people, companies, connections) -> None
    def intro_paths(self, user_id, company_name, max_hops=4) -> list[list[str]]
```
- `people`, `companies`, `connections` are plain dataclasses or the ORM rows' relevant
  fields (id, name, company_id; connection from/to/relation). To keep the store decoupled
  from SQLAlchemy, a small `GraphSnapshot` dataclass carries the data.

### Neo4jGraphStore (`app/graph/neo4j_store.py`)
- Holds a `neo4j` driver built from `settings.neo4j_uri/username/password`.
- `sync_user_graph`: in one transaction, delete the user's existing nodes
  (`MATCH (n {user_id:$uid}) DETACH DELETE n`), then MERGE a `You` node, `Person` nodes,
  `Company` nodes, `WORKS_AT` edges, person-to-person relationship edges, and `You KNOWS`
  edges to first-degree people (no incoming connection), all carrying `user_id`.
- `intro_paths`: Cypher variable-length path from the `You` node through
  `KNOWS|REFERRED|CAN_INTRO` to a `Person` who has `WORKS_AT` the company, returning the
  node names along each path, shortest first, limited to a few results.

### FakeGraphStore (`tests/fakes.py` or `app/graph/fake.py`)
- Stores the last synced snapshot in memory and implements `intro_paths` with a plain
  breadth-first search over the same node and edge model, returning identical
  name-path output. This is what tests use, so no Neo4j is required.

### Endpoints
- `POST /graph/sync` (JWT): builds a `GraphSnapshot` from Postgres and calls
  `sync_user_graph`. Returns `{ "people": n, "companies": n, "connections": n }`.
- `GET /intro-paths?company=<name>` (JWT): returns `{ "company": name, "paths": [[...names...]] }`.

### Config and dependency
- `settings` gains `neo4j_uri`, `neo4j_username`, `neo4j_password`, `neo4j_database`
  (all default empty; real values live in gitignored `backend/.env`).
- `get_graph_store()` returns a `Neo4jGraphStore` from settings; tests override it with a
  `FakeGraphStore`.

### Frontend
- A search row: company input plus "Find intro paths" button calling `/intro-paths`,
  rendering each path as `You -> Dipunj -> Rahul -> Qualcomm`.
- After a successful add or paste, the page calls `POST /graph/sync` (best effort, ignore
  failures) so the mirror tracks Postgres. A visible "Sync" button does the same on demand.

## Testing
- `GraphStore` contract via `FakeGraphStore`: after `sync_user_graph` with a small snapshot
  (You knows Dipunj, Dipunj knows Rahul, Rahul works at Qualcomm), `intro_paths(..,
  "Qualcomm")` returns `["You", "Dipunj", "Rahul", "Qualcomm"]`; an unknown company returns `[]`.
- `POST /graph/sync` and `GET /intro-paths` endpoint tests with `get_graph_store` overridden
  by a `FakeGraphStore`: sync then query returns the expected path; auth required; scoped per
  user.
- Real Aura connection: `backend/scripts/smoke_neo4j.py` syncs a tiny graph to Aura and
  prints `intro_paths`. Manual, not part of the hermetic suite.

## Files (planned)
```
backend/app/graph/__init__.py
backend/app/graph/base.py            GraphStore ABC + GraphSnapshot
backend/app/graph/fake.py            FakeGraphStore (in-memory BFS)
backend/app/graph/neo4j_store.py     Neo4jGraphStore (driver + Cypher)
backend/app/config.py                neo4j_* settings
backend/app/deps.py                  get_graph_store
backend/app/services/graph_sync.py   build_snapshot(db, user_id) -> GraphSnapshot
backend/app/routers/intro.py         POST /graph/sync, GET /intro-paths
backend/app/main.py                  include intro router
frontend/index.html                  intro-paths box + auto-sync
backend/scripts/smoke_neo4j.py       live Aura smoke test
backend/requirements.txt             add neo4j
backend/tests/test_intro.py          GraphStore + endpoint tests
```
