# Kith

Relationship intelligence platform. Reads your messages, extracts people and the
companies they are tied to, maps the network, and tells you who to follow up with.

## Phase 0: backend skeleton

FastAPI service with JWT auth, backed by Postgres. Neo4j and Qdrant run alongside
for later phases.

### Run the full stack

    docker compose up --build

API at http://localhost:8000, docs at http://localhost:8000/docs.

### Run tests (no containers needed)

    cd backend
    python -m venv .venv
    pip install -r requirements-dev.txt
    pytest -v

## Endpoints

- GET /health
- POST /auth/register returns a JWT
- POST /auth/login returns a JWT
- GET /auth/me returns current user (requires bearer token)
