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
- POST /paste extracts people and companies from a message (requires bearer token)
- GET /graph returns your network as nodes and edges (requires bearer token)

## Run it locally and see your network (no Docker)

From the `backend` directory, run the app against a local SQLite file:

PowerShell:

    $env:DATABASE_URL = "sqlite:///./kith_local.db"
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Then open http://localhost:8000 in your browser. Register, paste an email or
message, and watch the network map fill in. The Gemini key in `backend/.env`
powers the extraction.
