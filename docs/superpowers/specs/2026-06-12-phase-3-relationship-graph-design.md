# Kith Phase 3: Relationship Graph

**Design spec** · 2026-06-12

## Purpose

Turn the network from "people next to their companies" into a real relationship graph:
capture how people are connected to each other (you know Dipunj; Dipunj knows Rahul),
so a second-degree contact like Rahul links to both the person who connects you to him
(Dipunj) and to his own company (Qualcomm) at the same time. Also stop the duplicate
problem: the same person mentioned twice should merge into one node.

## Scope

### In scope (Phase 3)
- A `connections` table (Postgres): directed person-to-person edges with a relation type
  (`knows`, `referred`, `can_intro`) and an optional note.
- A **Resolver**: when a person is created (by manual add or by extraction), match an
  existing person of the same user by normalized name (case-insensitive, trimmed) and
  reuse it instead of creating a duplicate.
- **Manual add gains a "known through" field**: adding a person and naming an existing
  contact creates a `knows` connection from that contact to the new person.
- **Relationship extraction**: the Extractor also returns person-to-person relationships,
  which ingestion turns into connections (both endpoints resolved through the Resolver).
- `GET /graph` returns the richer graph: a synthetic `You` node linked to first-degree
  contacts, plus person-to-person edges and the existing `WORKS_AT` edges.
- Frontend: a "known through" input on the add form, and rendering of the new edge types
  (person-to-person edges styled distinctly from `WORKS_AT`), with the `You` node centered.

### Explicitly deferred to the next phase
- The "who can get me into <company>?" warm-path query (multi-hop traversal). The data and
  edges it needs are built here; the query and its UI come next.
- **Neo4j**. Phase 3 runs on Postgres so there is no cloud signup friction. Neo4j is added
  in the following phase as the queryable graph store (free Aura tier), mirroring these
  same connections, and is what powers the warm-path query at scale.

## Success criteria
- Adding "Rahul", company "Qualcomm", known through "Dipunj" creates Rahul once, links him
  `WORKS_AT` Qualcomm and `Dipunj knows Rahul`, and the graph shows Rahul connected to both
  Dipunj and Qualcomm.
- Adding or extracting the same person name twice does not create duplicate person nodes.
- Pasting "Dipunj's friend Rahul is an SDE at Qualcomm" produces the same structure.
- `GET /graph` shows a `You` node connected to people you know directly, with
  second-degree people hanging off their introducer.
- All covered by hermetic tests (SQLite, fake LLM); no Neo4j required.

## Architecture

### Data model (Postgres)
- New table `connections`: `id`, `user_id`, `from_person_id`, `to_person_id`,
  `relation_type` (string: `knows` / `referred` / `can_intro`), `note` (nullable),
  `source_message_id` (nullable), `created_at`.
- `Person` and `Company` unchanged. Postgres remains the source of truth.

### Resolver (`app/services/resolver.py`)
- `resolve_person(db, user_id, name) -> Person`: look up an existing person for the user
  by normalized name (lowercased, stripped); return it if found, else create and return a
  new one. Replaces the raw `Person(...)` creation in ingestion and manual add so dedup is
  consistent everywhere.

### Extraction changes
- `ExtractionResult` gains `relationships: list[ExtractedRelationship]`, where each has
  `from_person` (name), `to_person` (name), `relation_type`, and optional `note`. The Gemini
  prompt is updated to capture "A introduced B", "A knows B", "A can intro you to B", etc.
- Ingestion resolves both endpoint names through the Resolver and creates `connections`.

### Manual add changes
- `PersonCreate` gains `known_through: Optional[str]`. If present, the named person is
  resolved (created if needed) and a `knows` connection from that person to the new person
  is created.

### Graph view (`GET /graph`)
- Nodes: a single `You` node (`id="you"`, `type="you"`); each person (`type="person"`);
  each company (`type="company"`).
- Edges:
  - `WORKS_AT`: person to company (as today).
  - relationship edges: `from` person to `to` person, labeled by relation type
    (`KNOWS` / `REFERRED` / `CAN_INTRO`).
  - `You` to each first-degree person, labeled `KNOWS`. A person is first-degree when no
    connection points to them (nobody introduced them, so you know them directly).

### Frontend
- The add form gets a third input, "known through (optional)".
- The graph renders the `You` node distinctly (centered, amber), person-to-person edges in
  a different color from `WORKS_AT`, keeping the existing floating physics.

## Data flow (worked example)
1. Add `Dipunj`, company `Cloudflare` (no "known through") -> Dipunj resolved/created,
   `Dipunj WORKS_AT Cloudflare`, and (no incoming connection) Dipunj is first-degree.
2. Add `Rahul`, company `Qualcomm`, known through `Dipunj` -> Rahul created, `Rahul
   WORKS_AT Qualcomm`, `Dipunj knows Rahul`.
3. `GET /graph` -> `You -> Dipunj` (KNOWS), `Dipunj -> Cloudflare` (WORKS_AT),
   `Dipunj -> Rahul` (KNOWS), `Rahul -> Qualcomm` (WORKS_AT). Rahul shows linked to both
   Dipunj and Qualcomm; he is not linked to `You` directly because he is second-degree.

## Testing
- Resolver: same name (any case/whitespace) returns the same person row; different names
  create different rows; scoped per user.
- Manual add with `known_through`: creates the person, the `WORKS_AT`, and the `knows`
  connection; `/graph` reflects all three; the introduced person is not a `You` edge.
- Extraction relationships: ingest with a fake LLM returning a relationship creates the
  connection with both endpoints deduped.
- `/graph`: `You` node present and linked to first-degree people only; person-to-person and
  `WORKS_AT` edges present; auth required; scoped per user.
- All hermetic (SQLite, fake LLM via dependency override).

## Files (planned)
```
backend/app/models/connection.py        Connection ORM
backend/app/models/__init__.py          register Connection
backend/app/services/resolver.py        resolve_person
backend/app/schemas/extraction.py       add ExtractedRelationship + relationships
backend/app/schemas/people.py           add known_through to PersonCreate
backend/app/services/ingest.py          use resolver, create connections
backend/app/services/people.py          use resolver, handle known_through
backend/app/services/graph_view.py      You node + relationship edges
backend/app/llm/gemini.py               prompt mentions relationships
frontend/index.html                     known-through input + edge styling
backend/tests/...                        resolver, connections, graph, ingest tests
```
