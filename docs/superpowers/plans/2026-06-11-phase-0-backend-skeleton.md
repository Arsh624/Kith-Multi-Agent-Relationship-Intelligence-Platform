# Kith Phase 0: Backend Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Kith backend skeleton: a containerized FastAPI service with Postgres, Neo4j, and Qdrant running via Docker Compose, plus working JWT authentication (register, login, protected route) and a health check.

**Architecture:** A single FastAPI app (sync SQLAlchemy 2.0) owns the Postgres users table. Auth is JWT bearer tokens: passwords hashed with bcrypt, tokens signed with HS256. Neo4j and Qdrant are started by Compose now so the stack is complete, but no app code touches them yet (that arrives in Phase 1 and Phase 2). Tests run hermetically against SQLite so they need no running containers; production uses Postgres via the `DATABASE_URL` env var.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Postgres 16 (psycopg2), PyJWT, bcrypt, pydantic-settings, pytest, httpx, Docker Compose.

---

## File Structure

```
backend/
  app/
    __init__.py
    main.py            FastAPI app: registers routers, creates tables
    config.py          Settings loaded from env via pydantic-settings
    database.py        SQLAlchemy engine, SessionLocal, Base, get_db
    security.py        bcrypt hashing + PyJWT token create/decode (pure functions)
    deps.py            get_current_user FastAPI dependency
    models/
      __init__.py
      user.py          User ORM model
    schemas/
      __init__.py
      auth.py          Pydantic request/response models
    routers/
      __init__.py
      health.py        GET /health
      auth.py          POST /auth/register, POST /auth/login, GET /auth/me
  tests/
    __init__.py
    conftest.py        env setup + client fixture (SQLite, fresh DB per test)
    test_health.py
    test_security.py
    test_auth.py
  requirements.txt     runtime deps
  requirements-dev.txt test deps
  Dockerfile
  .env.example
docker-compose.yml     db, neo4j, qdrant, api
.gitignore
README.md
```

Each file has one responsibility. `security.py` holds only pure functions (no DB, no FastAPI) so it is trivially unit-testable. Routers are thin and delegate to `security.py` and the ORM.

---

## Task 0: Project scaffolding

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/.env.example`
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/models/__init__.py` (empty)
- Create: `backend/app/schemas/__init__.py` (empty)
- Create: `backend/app/routers/__init__.py` (empty)
- Create: `backend/tests/__init__.py` (empty)

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
venv/
.env
*.db
.pytest_cache/
node_modules/
.DS_Store
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
pydantic[email]==2.10.4
pydantic-settings==2.7.1
bcrypt==4.2.1
pyjwt==2.10.1
```

- [ ] **Step 3: Create `backend/requirements-dev.txt`**

```text
-r requirements.txt
pytest==8.3.4
httpx==0.28.1
```

- [ ] **Step 4: Create `backend/.env.example`**

```text
DATABASE_URL=postgresql+psycopg2://kith:kith@localhost:5432/kith
JWT_SECRET=dev-secret-change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

- [ ] **Step 5: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: kith
      POSTGRES_PASSWORD: kith
      POSTGRES_DB: kith
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kith"]
      interval: 5s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/kithkithkith
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4jdata:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrantdata:/qdrant/storage

  api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg2://kith:kith@db:5432/kith
      JWT_SECRET: dev-secret-change-me
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
  neo4jdata:
  qdrantdata:
```

- [ ] **Step 7: Create empty package files**

Create these as empty files:
- `backend/app/__init__.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/routers/__init__.py`
- `backend/tests/__init__.py`

- [ ] **Step 8: Create `README.md`**

```markdown
# Kith

Relationship intelligence platform. Reads your messages, extracts people and the
companies they are tied to, maps the network, and tells you who to follow up with.

## Phase 0: backend skeleton

FastAPI service with JWT auth, backed by Postgres. Neo4j and Qdrant run alongside
for later phases.

### Run the full stack

```bash
docker compose up --build
```

API at http://localhost:8000, docs at http://localhost:8000/docs.

### Run tests (no containers needed)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -v
```

## Endpoints

- `GET /health`
- `POST /auth/register` -> returns a JWT
- `POST /auth/login` -> returns a JWT
- `GET /auth/me` -> current user (requires bearer token)
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "chore: scaffold Phase 0 project structure and Docker stack"
```

---

## Task 1: Config and database wiring

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

No tests here (pure wiring exercised by later tasks). Keep it minimal.

- [ ] **Step 1: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://kith:kith@localhost:5432/kith"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24


settings = Settings()
```

- [ ] **Step 2: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url, pool_pre_ping=True, connect_args=connect_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py backend/app/database.py
git commit -m "feat: add settings and SQLAlchemy engine wiring"
```

---

## Task 2: Password hashing (TDD)

**Files:**
- Create: `backend/app/security.py`
- Test: `backend/tests/conftest.py`, `backend/tests/test_security.py`

- [ ] **Step 1: Create `backend/tests/conftest.py`**

This sets env vars to a hermetic SQLite database before any app module imports settings.

```python
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_kith.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    db_path = "test_kith.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.database import Base, engine
    from app.models import user  # noqa: F401  registers the table

    Base.metadata.create_all(bind=engine)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)
```

- [ ] **Step 2: Write the failing test in `backend/tests/test_security.py`**

```python
from app.security import hash_password, verify_password


def test_hash_password_is_not_plaintext():
    hashed = hash_password("hunter2")
    assert hashed != "hunter2"
    assert len(hashed) > 0


def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True
    assert verify_password("wrong", hashed) is False
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.security'` (or import error).

- [ ] **Step 4: Create `backend/app/security.py` with the hashing functions**

```python
import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/security.py backend/tests/conftest.py backend/tests/test_security.py
git commit -m "feat: add bcrypt password hashing with tests"
```

---

## Task 3: JWT tokens (TDD)

**Files:**
- Modify: `backend/app/security.py`
- Test: `backend/tests/test_security.py`

- [ ] **Step 1: Add the failing tests to `backend/tests/test_security.py`**

Append:

```python
from app.security import create_access_token, decode_access_token


def test_token_roundtrip_returns_subject():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_decode_rejects_garbage_token():
    assert decode_access_token("not-a-real-token") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: FAIL with `ImportError: cannot import name 'create_access_token'`.

- [ ] **Step 3: Add the token functions to `backend/app/security.py`**

Add these imports at the top and functions at the bottom:

```python
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_security.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/tests/test_security.py
git commit -m "feat: add JWT create and decode with tests"
```

---

## Task 4: User model

**Files:**
- Create: `backend/app/models/user.py`

No standalone test; exercised by the auth tests in Task 7.

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/user.py
git commit -m "feat: add User ORM model"
```

---

## Task 5: Auth schemas and health router

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/routers/health.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
```

- [ ] **Step 2: Create `backend/app/routers/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Write the failing test in `backend/tests/test_health.py`**

```python
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'` (main.py does not exist yet).

- [ ] **Step 5: Create `backend/app/main.py`**

```python
from fastapi import FastAPI

from app.database import Base, engine
from app.models import user  # noqa: F401  registers the User table
from app.routers import auth, health

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)
```

Note: `app.routers.auth` is created in Task 6. Until then this import fails, so do not run the full suite yet; that is expected. Proceed to Task 6 which creates it. If you want to verify the health route in isolation right now, temporarily comment out the two `auth` lines, run the test, then restore them.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/routers/health.py backend/tests/test_health.py backend/app/main.py
git commit -m "feat: add auth schemas, health route, and app entrypoint"
```

---

## Task 6: get_current_user dependency

**Files:**
- Create: `backend/app/deps.py`

Exercised by the `/auth/me` test in Task 8.

- [ ] **Step 1: Create `backend/app/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/deps.py
git commit -m "feat: add get_current_user JWT dependency"
```

---

## Task 7: Register and login endpoints (TDD)

**Files:**
- Create: `backend/app/routers/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_auth.py`**

```python
def test_register_returns_token(client):
    response = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 0


def test_register_duplicate_email_fails(client):
    client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    response = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "other"},
    )
    assert response.status_code == 400


def test_login_succeeds_with_correct_password(client):
    client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    assert response.status_code == 200
    assert len(response.json()["access_token"]) > 0


def test_login_fails_with_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "nope"},
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: FAIL at import (`app.main` imports `app.routers.auth`, which does not exist yet).

- [ ] **Step 3: Create `backend/app/routers/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email, hashed_password=hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat: add register and login endpoints with tests"
```

---

## Task 8: Protected /auth/me route (TDD)

**Files:**
- Test: `backend/tests/test_auth.py`

The route already exists from Task 7. This task proves the JWT protection works end to end.

- [ ] **Step 1: Add the failing tests to `backend/tests/test_auth.py`**

Append:

```python
def test_me_returns_current_user_with_valid_token(client):
    register = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "hunter2"},
    )
    token = register.json()["access_token"]
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


def test_me_rejects_missing_token(client):
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: PASS (7 passed total in the file). These pass without new app code because Task 7 already implemented `/auth/me`. If any fail, fix the implementation in `app/routers/auth.py` or `app/deps.py` before continuing.

Note on the missing-token case: FastAPI's `HTTPBearer` returns 403 when the `Authorization` header is absent, and our dependency returns 401 for a present-but-invalid token. The test accepts either 401 or 403 for the missing case, and requires 401 for the invalid case.

- [ ] **Step 3: Run the whole suite**

Run: `cd backend && pytest -v`
Expected: PASS (all tests across test_security.py, test_health.py, test_auth.py).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_auth.py
git commit -m "test: cover protected /auth/me route end to end"
```

---

## Task 9: Verify the full Docker stack

**Files:** none (verification only).

- [ ] **Step 1: Build and start the stack**

Run: `docker compose up --build -d`
Expected: four containers start (db, neo4j, qdrant, api). Give them up to a minute.

- [ ] **Step 2: Check the API health**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 3: Register a user against the real Postgres**

Run:
```bash
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d "{\"email\":\"demo@example.com\",\"password\":\"hunter2\"}"
```
Expected: JSON with an `access_token`.

- [ ] **Step 4: Confirm Neo4j and Qdrant are reachable**

Run: `curl http://localhost:7474` (Neo4j browser, expect HTTP 200) and `curl http://localhost:6333/healthz` (Qdrant, expect an ok response).
Expected: both respond. This proves the stack the later phases need is live.

- [ ] **Step 5: Tear down**

Run: `docker compose down`
Expected: containers stop. Data volumes persist for next time.

- [ ] **Step 6: Commit any fixes**

If steps above required changes (for example, a Compose port tweak), commit them:
```bash
git add -A
git commit -m "fix: adjust Docker stack after end-to-end verification"
```

---

## Self-Review

**Spec coverage (Phase 0 slice of section 6):** Docker Compose with Postgres, Neo4j, Qdrant, FastAPI (Task 0, Task 9), health check (Task 5), JWT auth with register/login/protected route (Tasks 2, 3, 6, 7, 8). The "login works, stack runs" definition of done is covered by Task 9. Later phases (1 through 5) are intentionally out of scope for this plan.

**Type consistency:** `User.id` is a `str` (uuid string), and `create_access_token` takes a `str` subject, `decode_access_token` returns `str | None`, `db.get(User, user_id)` looks up by the same string id. `TokenResponse`, `UserResponse`, `RegisterRequest`, `LoginRequest` names match between `schemas/auth.py` and `routers/auth.py`. `get_current_user` is defined in `deps.py` and imported in `routers/auth.py`.

**Placeholder scan:** No TBDs. Every code step shows complete code. Every test step shows the assertions.

**Known pragmatic choice:** tests use SQLite for speed and hermeticity while production uses Postgres. The users table uses only portable column types, so this divergence is safe for Phase 0. Phases that depend on Postgres, Neo4j, or Qdrant specifics will test against the real containers.
