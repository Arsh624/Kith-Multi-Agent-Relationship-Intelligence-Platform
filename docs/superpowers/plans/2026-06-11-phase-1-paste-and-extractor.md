# Kith Phase 1: Paste Ingestion and Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `POST /paste` endpoint that takes a raw message, uses Gemini to extract the people and companies mentioned, and persists them to the database, returning the structured result.

**Architecture:** A provider-agnostic `LLMClient` interface (one method, `extract_entities`) with a `GeminiClient` implementation using Google's structured-output mode. An `ingest_message` service saves the raw message, calls the LLM, deduplicates companies, and creates Person rows linked to their Company and source Message. The endpoint is synchronous and JWT-protected (reusing Phase 0 auth). Tests inject a fake LLM client through FastAPI dependency overrides, so the suite never calls Gemini (free and hermetic). LangGraph is intentionally NOT introduced here; it arrives in a later phase when multiple agents need orchestrating.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, google-genai SDK (Gemini), pytest. Builds on the Phase 0 skeleton.

---

## Context for the implementer

The Phase 0 backend already exists under `backend/` and is fully working (12 passing tests):
- `app/config.py` exposes a `settings` object (pydantic-settings, reads env vars then `.env`).
- `app/database.py` exposes `Base`, `engine`, `SessionLocal`, `get_db`.
- `app/security.py`, `app/deps.py` (with `get_current_user`), `app/models/user.py` (User), `app/schemas/auth.py`, `app/routers/health.py`, `app/routers/auth.py`, `app/main.py`.
- `tests/conftest.py` sets env vars to a hermetic SQLite DB and provides a `client` fixture (FastAPI TestClient).
- A virtualenv exists at `backend/.venv` (Python 3.11) with all deps. Run pytest via PowerShell from the `backend` directory:
  `.\.venv\Scripts\python.exe -m pytest -v`
- `backend/.env` exists (gitignored) and already contains `GEMINI_API_KEY=...` and the other settings. NEVER print the key, never commit `.env`.

All commits in this repo avoid em dashes and en dashes. Do not use them in code, comments, or commit messages.

## File Structure (Phase 1 additions)

```
backend/
  app/
    config.py                MODIFY: add gemini_api_key, gemini_model
    deps.py                  MODIFY: add get_llm_client dependency
    main.py                  MODIFY: include the paste router
    schemas/
      extraction.py          NEW: ExtractedCompany, ExtractedPerson, ExtractionResult (the LLM contract)
      paste.py               NEW: PasteRequest, CompanyOut, PersonOut, PasteResponse (the API contract)
    llm/
      __init__.py            NEW: empty
      base.py                NEW: LLMClient abstract base (extract_entities)
      gemini.py              NEW: GeminiClient implementation
    models/
      __init__.py            MODIFY: import all models so their tables register
      message.py             NEW: Message ORM
      company.py             NEW: Company ORM
      person.py              NEW: Person ORM
    services/
      __init__.py            NEW: empty
      ingest.py              NEW: ingest_message + IngestResult
    routers/
      paste.py               NEW: POST /paste
  tests/
    conftest.py              MODIFY: add gemini env vars + a db_session fixture
    fakes.py                 NEW: FakeLLMClient test double
    test_gemini_client.py    NEW
    test_ingest.py           NEW
    test_paste.py            NEW
  scripts/
    smoke_extract.py         NEW: manual real-Gemini smoke test
  requirements.txt           MODIFY: add google-genai
```

---

## Task 1: Dependency, config, and schemas

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/schemas/extraction.py`
- Create: `backend/app/schemas/paste.py`

- [ ] **Step 1: Add the google-genai dependency and install it**

Append this line to `backend/requirements.txt`:
```text
google-genai>=1.0.0
```
Then install into the venv (PowerShell, from the `backend` directory):
`.\.venv\Scripts\python.exe -m pip install "google-genai>=1.0.0"`
Then record the exact installed version:
`.\.venv\Scripts\python.exe -m pip show google-genai`
Replace the `google-genai>=1.0.0` line in `requirements.txt` with the exact pinned version you just installed, for example `google-genai==1.21.0` (use the real version from pip show).

- [ ] **Step 2: Verify the SDK imports**

Run (from the `backend` directory):
`.\.venv\Scripts\python.exe -c "from google import genai; from google.genai import types; print('genai ok')"`
Expected: prints `genai ok`.

- [ ] **Step 3: Add Gemini settings to `backend/app/config.py`**

The current `Settings` class body ends with `access_token_expire_minutes`. Add two fields so the class reads:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://kith:kith@localhost:5432/kith"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"


settings = Settings()
```

- [ ] **Step 4: Add gemini env vars to `backend/tests/conftest.py`**

The top of conftest sets several `os.environ[...]` values before importing app modules. Add two more lines in that same block so tests never depend on the real `.env`:
```python
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
```
Place them alongside the existing `os.environ["JWT_SECRET"] = ...` lines (after them, before the `import pytest` line).

- [ ] **Step 5: Create `backend/app/schemas/extraction.py` (the LLM contract)**

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


class ExtractionResult(BaseModel):
    companies: list[ExtractedCompany] = []
    people: list[ExtractedPerson] = []
```

- [ ] **Step 6: Create `backend/app/schemas/paste.py` (the API contract)**

```python
from typing import Optional

from pydantic import BaseModel


class PasteRequest(BaseModel):
    source: str
    text: str


class CompanyOut(BaseModel):
    id: str
    name: str


class PersonOut(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None


class PasteResponse(BaseModel):
    message_id: str
    companies: list[CompanyOut]
    people: list[PersonOut]
```

- [ ] **Step 7: Confirm the suite still passes (nothing wired yet)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 12 passed (unchanged). The new schema modules are not imported anywhere yet, so nothing should break.

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/tests/conftest.py backend/app/schemas/extraction.py backend/app/schemas/paste.py
git commit -m "feat: add gemini config and extraction/paste schemas"
```

---

## Task 2: LLM interface and GeminiClient (TDD)

**Files:**
- Create: `backend/app/llm/__init__.py` (empty)
- Create: `backend/app/llm/base.py`
- Create: `backend/app/llm/gemini.py`
- Test: `backend/tests/test_gemini_client.py`

- [ ] **Step 1: Create the empty package file `backend/app/llm/__init__.py`** (no content)

- [ ] **Step 2: Create `backend/app/llm/base.py`**

```python
from abc import ABC, abstractmethod

from app.schemas.extraction import ExtractionResult


class LLMClient(ABC):
    @abstractmethod
    def extract_entities(self, text: str) -> ExtractionResult:
        """Extract people and companies from a raw message."""
        raise NotImplementedError
```

- [ ] **Step 3: Write the failing test `backend/tests/test_gemini_client.py`**

```python
from app.llm.gemini import GeminiClient
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractionResult,
)


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeModels:
    def __init__(self, parsed):
        self._parsed = parsed
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.models = _FakeModels(parsed)


def test_gemini_client_returns_parsed_result():
    expected = ExtractionResult(
        companies=[ExtractedCompany(name="Stripe")],
        people=[
            ExtractedPerson(
                name="Priya", title="PM", company="Stripe", note="offered intro"
            )
        ],
    )
    client = GeminiClient(api_key="test", model="gemini-2.5-flash")
    client._client = _FakeClient(expected)

    result = client.extract_entities("some email text")

    assert result == expected
    assert client._client.models.last_kwargs["model"] == "gemini-2.5-flash"


def test_gemini_client_handles_none_parsed():
    client = GeminiClient(api_key="test", model="gemini-2.5-flash")
    client._client = _FakeClient(None)

    result = client.extract_entities("text")

    assert result == ExtractionResult()
```

- [ ] **Step 4: Run the test and confirm it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gemini_client.py -v`
Expected: import error, `app.llm.gemini` does not exist yet.

- [ ] **Step 5: Create `backend/app/llm/gemini.py`**

```python
from google import genai
from google.genai import types

from app.llm.base import LLMClient
from app.schemas.extraction import ExtractionResult

EXTRACTION_PROMPT = (
    "You extract professional networking information from a message. "
    "Identify the people mentioned and the companies they are associated with. "
    "For each person, capture their name, their job title if stated, the company "
    "they are associated with if stated, and a short note about anything relevant "
    "they said or offered. List each distinct company by name. Only include "
    "information that is actually present in the message. Do not invent people or "
    "companies.\n\nMessage:\n"
)


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract_entities(self, text: str) -> ExtractionResult:
        response = self._client.models.generate_content(
            model=self._model,
            contents=EXTRACTION_PROMPT + text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractionResult,
            ),
        )
        result = response.parsed
        if result is None:
            return ExtractionResult()
        return result
```

- [ ] **Step 6: Run the test and confirm it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gemini_client.py -v`
Expected: 2 passed.

If `GeminiClient(api_key="test", ...)` raises during construction (some SDK versions validate the key), report it as BLOCKED with the exact error; the fix is to make the client construction lazy, but do not change the approach without flagging it first.

- [ ] **Step 7: Commit**

```bash
git add backend/app/llm/__init__.py backend/app/llm/base.py backend/app/llm/gemini.py backend/tests/test_gemini_client.py
git commit -m "feat: add LLMClient interface and GeminiClient with tests"
```

---

## Task 3: ORM models for Message, Company, Person

**Files:**
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/company.py`
- Create: `backend/app/models/person.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/message.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Create `backend/app/models/company.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 3: Create `backend/app/models/person.py`**

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("companies.id"), nullable=True
    )
    source_message_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("messages.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 4: Replace `backend/app/models/__init__.py` with imports of every model**

This makes every table register on `Base.metadata` whenever the package is imported (the test fixtures and `main.py` rely on this for `create_all`).
```python
from app.models.user import User
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person

__all__ = ["User", "Company", "Message", "Person"]
```

- [ ] **Step 5: Verify all tables register**

Run (from the `backend` directory):
`.\.venv\Scripts\python.exe -c "import app.models; from app.database import Base; print(sorted(Base.metadata.tables))"`
Expected: prints `['companies', 'messages', 'people', 'users']`.

- [ ] **Step 6: Confirm the full suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 14 passed (12 from before plus the 2 GeminiClient tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/message.py backend/app/models/company.py backend/app/models/person.py backend/app/models/__init__.py
git commit -m "feat: add Message, Company, and Person models"
```

---

## Task 4: Ingest service (TDD)

**Files:**
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/services/ingest.py`
- Create: `backend/tests/fakes.py`
- Modify: `backend/tests/conftest.py` (add a `db_session` fixture)
- Test: `backend/tests/test_ingest.py`

- [ ] **Step 1: Create the empty package file `backend/app/services/__init__.py`** (no content)

- [ ] **Step 2: Create `backend/tests/fakes.py`**

```python
from app.llm.base import LLMClient
from app.schemas.extraction import ExtractionResult


class FakeLLMClient(LLMClient):
    def __init__(self, result: ExtractionResult) -> None:
        self._result = result

    def extract_entities(self, text: str) -> ExtractionResult:
        return self._result
```

- [ ] **Step 3: Add a `db_session` fixture to `backend/tests/conftest.py`**

Append this fixture to the end of conftest (it gives tests a raw SQLAlchemy session against the hermetic SQLite DB):
```python
@pytest.fixture()
def db_session():
    db_path = "test_kith.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.database import Base, SessionLocal, engine
    import app.models  # noqa: F401  registers all tables

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)
```

- [ ] **Step 4: Write the failing test `backend/tests/test_ingest.py`**

```python
from sqlalchemy import select

from app.models.company import Company
from app.models.person import Person
from app.models.user import User
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
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


def test_ingest_creates_message_people_and_companies(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(
                    name="Priya Sharma",
                    title="PM",
                    company="Stripe",
                    note="offered intro",
                )
            ],
        )
    )

    result = ingest_message(db_session, user.id, "email", "raw text", fake)

    assert result.message.processed is True
    assert len(result.companies) == 1
    assert result.companies[0].name == "Stripe"
    assert len(result.people) == 1

    person = db_session.scalars(select(Person)).one()
    assert person.name == "Priya Sharma"
    assert person.title == "PM"
    assert person.note == "offered intro"
    assert person.company_id == result.companies[0].id
    assert person.source_message_id == result.message.id


def test_ingest_dedupes_companies_within_one_message(db_session):
    user = _make_user(db_session)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(name="A", company="Stripe"),
                ExtractedPerson(name="B", company="Stripe"),
            ],
        )
    )

    ingest_message(db_session, user.id, "email", "raw", fake)

    companies = db_session.scalars(select(Company)).all()
    assert len(companies) == 1
```

- [ ] **Step 5: Run the test and confirm it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_ingest.py -v`
Expected: import error, `app.services.ingest` does not exist yet.

- [ ] **Step 6: Create `backend/app/services/ingest.py`**

```python
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.base import LLMClient
from app.models.company import Company
from app.models.message import Message
from app.models.person import Person


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

    company_by_name: dict[str, Company] = {}
    for extracted in extraction.companies:
        company_by_name[extracted.name] = _get_or_create_company(
            db, user_id, extracted.name
        )

    people: list[Person] = []
    for extracted in extraction.people:
        company = None
        if extracted.company:
            company = company_by_name.get(extracted.company)
            if company is None:
                company = _get_or_create_company(db, user_id, extracted.company)
                company_by_name[extracted.company] = company
        person = Person(
            user_id=user_id,
            name=extracted.name,
            title=extracted.title,
            note=extracted.note,
            company_id=company.id if company is not None else None,
            source_message_id=message.id,
        )
        db.add(person)
        people.append(person)

    message.processed = True
    db.commit()
    db.refresh(message)
    return IngestResult(
        message=message, companies=list(company_by_name.values()), people=people
    )


def _get_or_create_company(db: Session, user_id: str, name: str) -> Company:
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

- [ ] **Step 7: Run the test and confirm it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_ingest.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/ingest.py backend/tests/fakes.py backend/tests/conftest.py backend/tests/test_ingest.py
git commit -m "feat: add ingest_message service with tests"
```

---

## Task 5: The /paste endpoint (TDD)

**Files:**
- Modify: `backend/app/deps.py` (add `get_llm_client`)
- Create: `backend/app/routers/paste.py`
- Modify: `backend/app/main.py` (include the paste router)
- Test: `backend/tests/test_paste.py`

- [ ] **Step 1: Add `get_llm_client` to `backend/app/deps.py`**

Add these imports at the top (alongside the existing imports) and the function at the end of the file:
```python
from app.config import settings
from app.llm.base import LLMClient
from app.llm.gemini import GeminiClient


def get_llm_client() -> LLMClient:
    return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
```

- [ ] **Step 2: Write the failing test `backend/tests/test_paste.py`**

```python
from app.deps import get_llm_client
from app.main import app
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractionResult,
)
from tests.fakes import FakeLLMClient


def _auth_token(client):
    response = client.post(
        "/auth/register",
        json={"email": "u@example.com", "password": "hunter2"},
    )
    return response.json()["access_token"]


def test_paste_extracts_and_persists(client):
    token = _auth_token(client)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(
                    name="Priya Sharma",
                    title="PM",
                    company="Stripe",
                    note="offered intro",
                )
            ],
        )
    )
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        response = client.post(
            "/paste",
            headers={"Authorization": f"Bearer {token}"},
            json={"source": "email", "text": "Priya is a PM at Stripe."},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 201
    body = response.json()
    assert body["message_id"]
    assert len(body["companies"]) == 1
    assert body["companies"][0]["name"] == "Stripe"
    assert len(body["people"]) == 1
    assert body["people"][0]["name"] == "Priya Sharma"
    assert body["people"][0]["company"] == "Stripe"
    assert body["people"][0]["note"] == "offered intro"


def test_paste_requires_auth(client):
    response = client.post(
        "/paste", json={"source": "email", "text": "hello"}
    )
    assert response.status_code in (401, 403)
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_paste.py -v`
Expected: failure because `/paste` returns 404 (route not wired yet). Record the output.

- [ ] **Step 4: Create `backend/app/routers/paste.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_llm_client
from app.llm.base import LLMClient
from app.models.user import User
from app.schemas.paste import CompanyOut, PasteRequest, PasteResponse, PersonOut
from app.services.ingest import ingest_message

router = APIRouter(tags=["ingest"])


@router.post("/paste", response_model=PasteResponse, status_code=status.HTTP_201_CREATED)
def paste(
    payload: PasteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
):
    result = ingest_message(
        db, current_user.id, payload.source, payload.text, llm
    )
    company_name_by_id = {c.id: c.name for c in result.companies}
    companies = [CompanyOut(id=c.id, name=c.name) for c in result.companies]
    people = [
        PersonOut(
            id=p.id,
            name=p.name,
            title=p.title,
            company=company_name_by_id.get(p.company_id),
            note=p.note,
        )
        for p in result.people
    ]
    return PasteResponse(
        message_id=result.message.id, companies=companies, people=people
    )
```

- [ ] **Step 5: Wire the paste router into `backend/app/main.py`**

The current file imports `from app.routers import auth, health` and includes both. Change it to also import and include `paste`, so the file reads:
```python
from fastapi import FastAPI

from app.database import Base, engine
from app.models import user  # noqa: F401  registers the User table
from app.routers import auth, health, paste

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kith API")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(paste.router)
```

- [ ] **Step 6: Run the paste tests and confirm they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_paste.py -v`
Expected: 2 passed.

- [ ] **Step 7: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: 18 passed (12 Phase 0 + 2 gemini + 2 ingest + 2 paste).

- [ ] **Step 8: Commit**

```bash
git add backend/app/deps.py backend/app/routers/paste.py backend/app/main.py backend/tests/test_paste.py
git commit -m "feat: add JWT-protected /paste endpoint with tests"
```

---

## Task 6: Real-Gemini smoke test (manual, needs the key and network)

**Files:**
- Create: `backend/scripts/smoke_extract.py`

This is a manual verification that the real Gemini integration works end to end. It calls the live API (uses a small amount of free-tier quota) and does not touch the database. It is not part of the hermetic pytest suite.

- [ ] **Step 1: Create `backend/scripts/smoke_extract.py`**

```python
from app.config import settings
from app.llm.gemini import GeminiClient

SAMPLE = (
    "Hey, great chatting earlier. I am a PM at Stripe. My friend Ravi leads "
    "recruiting at Notion, you two should connect. Ping me next week and I will "
    "introduce you."
)


def main() -> None:
    client = GeminiClient(
        api_key=settings.gemini_api_key, model=settings.gemini_model
    )
    result = client.extract_entities(SAMPLE)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it against the real API**

Run (from the `backend` directory, which loads `.env` with the real key):
`.\.venv\Scripts\python.exe scripts\smoke_extract.py`
Expected: JSON listing Stripe and Notion as companies, and Priya-style/Ravi people with their companies. The exact wording will vary (it is a real model), but it should correctly identify both companies and the people, with the recruiting/intro note captured. If it errors on auth, the key in `.env` is wrong or not enabled; report the error WITHOUT printing the key.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_extract.py
git commit -m "chore: add manual gemini smoke test script"
```

---

## Self-Review

**Spec coverage (Phase 1 slice of spec section 6, "Capture and Extract"):**
- `/paste` endpoint: Task 5.
- Extractor agent using Gemini, returning structured people and companies: Tasks 2 and 4.
- Saved to Postgres (Message, Company, Person): Tasks 3 and 4.
- Provider-agnostic / BYOK interface: Task 2 (`LLMClient` plus `GeminiClient`, swapped via `get_llm_client`).
- JWT protection reused from Phase 0: Task 5.
- Gmail auto-sync is explicitly deferred to a later Phase 1 increment (spec says "layered on after paste works") and is NOT in this plan.
- "Threads"/follow-ups are intentionally out of scope here (they belong to Phase 3); extraction captures people and companies only.

**Type consistency:** `LLMClient.extract_entities(text) -> ExtractionResult` is implemented by `GeminiClient` and `FakeLLMClient` with the same signature. `ingest_message(db, user_id, source, text, llm) -> IngestResult` is called identically in `test_ingest.py` and `routers/paste.py`. `IngestResult` exposes `.message`, `.companies`, `.people`, all used consistently. `ExtractedPerson.company` is a company name string (not an id); `ingest_message` maps it to a `Company.id`; `PersonOut.company` is again the name, resolved via `company_name_by_id`. Schema class names (`ExtractedCompany`, `ExtractedPerson`, `ExtractionResult`, `PasteRequest`, `CompanyOut`, `PersonOut`, `PasteResponse`) match across all tasks.

**Placeholder scan:** No TBDs. Every code step is complete. Every test shows real assertions and exact run commands with expected counts (12 then 14 then 18).

**Known pragmatic choices (acceptable for Phase 1):** person-level deduplication is not done (pasting the same email twice creates duplicate people); that is the Resolver agent's job in Phase 2 (semantic dedup via Qdrant). Company dedup is exact-name match within the user's scope. Extraction is synchronous in the request. `create_all` still runs at `main.py` import (carried over from Phase 0; move to a lifespan handler or Alembic in a later phase).
