# Kith Phase 7: Contact Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each person a contact card (role plus email, phone, LinkedIn) stored in a new `contacts` table, exposed via `GET`/`PATCH /people/{id}`, and shown as a click-to-edit panel in the Map with Email (Gmail compose) and LinkedIn buttons.

**Architecture:** A new `contacts` table (one row per person, so `create_all` adds it with no migration) holds email/phone/linkedin; the role reuses `Person.title`. A thin service upserts contacts; two new endpoints on the people router read and update the card. The frontend opens a detail panel on person click.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, pytest, vanilla JS. Builds on Phases 0 to 6.

---

## Context for the implementer

Phases 0 to 6 are complete (64 passing tests). Relevant:
- `app/models/person.py` `Person(id, user_id, name, title, note, company_id, source_message_id)`; `app/models/company.py` `Company`. Models registered in `app/models/__init__.py`.
- `app/schemas/people.py` currently has `PersonCreate(name, company, known_through)`.
- `app/routers/people.py` has `POST /people`, `DELETE /people/{person_id}`; it imports `APIRouter, Depends, HTTPException, status`, `Session`, `get_db`, `get_current_user`, `Company`, `User`, `PersonOut` (from `app.schemas.paste`), `PersonCreate`, and from `app.services.people`: `KnownThroughNotFound, add_person, delete_person`.
- `app/deps.py` `get_current_user`; `app/database.py` `get_db`, `Base`.
- `tests/conftest.py` has `client` and `db_session`.
- `frontend/index.html`: Map view has the graph; `onNodeClick(params)` currently prefills the known-through input when a person node is clicked. `api()` returns parsed JSON or null (204). `loadGraph()` exists.
- Run from `backend`: `.\.venv\Scripts\python.exe -m pytest -q`.

No em dashes or en dashes anywhere.

## File Structure (Phase 7)

```
backend/app/models/contact.py          NEW Contact ORM
backend/app/models/__init__.py         MODIFY register Contact
backend/app/services/contacts.py       NEW get_contact, upsert_contact
backend/app/schemas/people.py          MODIFY add PersonDetail, PersonPatch
backend/app/routers/people.py          MODIFY add GET + PATCH /people/{id}
frontend/index.html                    MODIFY detail panel + Email/LinkedIn buttons
backend/tests/test_contacts.py         NEW hermetic tests
```

---

## Task 1: Contact model

**Files:**
- Create: `backend/app/models/contact.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/contact.py`**

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    person_id: Mapped[str] = mapped_column(
        String, ForeignKey("people.id"), unique=True, nullable=False, index=True
    )
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
from app.models.task import Task
from app.models.contact import Contact

__all__ = [
    "User",
    "Company",
    "Message",
    "Person",
    "Connection",
    "Task",
    "Contact",
]
```

- [ ] **Step 3: Verify and run the suite**

Run: `.\.venv\Scripts\python.exe -c "import app.models; from app.database import Base; print('contacts' in Base.metadata.tables)"`
Expected: `True`.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 64 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/contact.py backend/app/models/__init__.py
git commit -m "feat: add Contact model for person contact details"
```

---

## Task 2: Contacts service and schemas (TDD)

**Files:**
- Create: `backend/app/services/contacts.py`
- Modify: `backend/app/schemas/people.py`
- Test: `backend/tests/test_contacts.py` (service part)

- [ ] **Step 1: Replace `backend/app/schemas/people.py` with EXACTLY:**

```python
from typing import Optional

from pydantic import BaseModel


class PersonCreate(BaseModel):
    name: str
    company: Optional[str] = None
    known_through: Optional[str] = None


class PersonDetail(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    note: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None


class PersonPatch(BaseModel):
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
```

- [ ] **Step 2: Write the failing test `backend/tests/test_contacts.py`**

```python
from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.services.contacts import get_contact, upsert_contact


def _make_user(db_session, email="c@example.com"):
    user = User(email=email, hashed_password=hash_password("x"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_person(db_session, user_id, name="Dipunj"):
    person = Person(user_id=user_id, name=name)
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)
    return person


def test_upsert_creates_then_updates_only_given_fields(db_session):
    user = _make_user(db_session)
    person = _make_person(db_session, user.id)

    upsert_contact(db_session, user.id, person.id, email="d@x.com", phone="123")
    db_session.commit()
    contact = get_contact(db_session, user.id, person.id)
    assert contact.email == "d@x.com"
    assert contact.phone == "123"
    assert contact.linkedin is None

    upsert_contact(db_session, user.id, person.id, linkedin="in/dipunj")
    db_session.commit()
    contact = get_contact(db_session, user.id, person.id)
    assert contact.email == "d@x.com"
    assert contact.linkedin == "in/dipunj"


def test_get_contact_scoped_to_user(db_session):
    owner = _make_user(db_session, "owner@example.com")
    other = _make_user(db_session, "other@example.com")
    person = _make_person(db_session, owner.id)
    upsert_contact(db_session, owner.id, person.id, email="d@x.com")
    db_session.commit()
    assert get_contact(db_session, other.id, person.id) is None
```

- [ ] **Step 3: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contacts.py -v`
Expected: import error (`app.services.contacts` does not exist).

- [ ] **Step 4: Create `backend/app/services/contacts.py`**

```python
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact


def get_contact(
    db: Session, user_id: str, person_id: str
) -> Optional[Contact]:
    return db.scalar(
        select(Contact).where(
            Contact.user_id == user_id, Contact.person_id == person_id
        )
    )


def upsert_contact(
    db: Session,
    user_id: str,
    person_id: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin: Optional[str] = None,
) -> Contact:
    contact = get_contact(db, user_id, person_id)
    if contact is None:
        contact = Contact(user_id=user_id, person_id=person_id)
        db.add(contact)
    if email is not None:
        contact.email = email
    if phone is not None:
        contact.phone = phone
    if linkedin is not None:
        contact.linkedin = linkedin
    db.flush()
    return contact
```

- [ ] **Step 5: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contacts.py -v`
Expected: 2 passed.

- [ ] **Step 6: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 66 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/contacts.py backend/app/schemas/people.py backend/tests/test_contacts.py
git commit -m "feat: add contact service and person detail schemas"
```

---

## Task 3: Person detail endpoints (TDD)

**Files:**
- Modify: `backend/app/routers/people.py`
- Test: `backend/tests/test_contacts.py` (endpoint part)

- [ ] **Step 1: Add the failing endpoint tests to `backend/tests/test_contacts.py`**

Append:
```python
def _register(client, email="cc@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_get_and_patch_person_detail(client):
    headers = _register(client)
    created = client.post(
        "/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"}
    )
    person_id = created.json()["id"]

    detail = client.get(f"/people/{person_id}", headers=headers).json()
    assert detail["name"] == "Dipunj"
    assert detail["company"] == "Cloudflare"
    assert detail["email"] is None

    patched = client.patch(
        f"/people/{person_id}",
        headers=headers,
        json={"title": "SDE1", "email": "d@x.com", "linkedin": "in/dipunj"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["title"] == "SDE1"
    assert body["email"] == "d@x.com"
    assert body["linkedin"] == "in/dipunj"

    again = client.patch(
        f"/people/{person_id}", headers=headers, json={"phone": "999"}
    ).json()
    assert again["phone"] == "999"
    assert again["email"] == "d@x.com"
    assert again["title"] == "SDE1"


def test_get_person_detail_unknown_returns_404(client):
    headers = _register(client)
    assert client.get("/people/nope", headers=headers).status_code == 404


def test_person_detail_requires_auth(client):
    assert client.get("/people/x").status_code in (401, 403)
    assert client.patch("/people/x", json={"title": "y"}).status_code in (401, 403)
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contacts.py -v`
Expected: the endpoint tests fail (GET/PATCH /people/{id} not wired, return 404 or 405).

- [ ] **Step 3: Update `backend/app/routers/people.py`**

Add these imports (merge with the existing import lines):
```python
from sqlalchemy import select

from app.models.person import Person
from app.schemas.people import PersonCreate, PersonDetail, PersonPatch
from app.services.contacts import get_contact, upsert_contact
```
(Keep the existing imports; `PersonCreate` may already be imported, do not duplicate it.)

Add a helper and the two endpoints at the end of the file:
```python
def _build_detail(db: Session, user_id: str, person: Person) -> PersonDetail:
    company_name = None
    if person.company_id is not None:
        company = db.get(Company, person.company_id)
        company_name = company.name if company is not None else None
    contact = get_contact(db, user_id, person.id)
    return PersonDetail(
        id=person.id,
        name=person.name,
        title=person.title,
        company=company_name,
        note=person.note,
        email=contact.email if contact is not None else None,
        phone=contact.phone if contact is not None else None,
        linkedin=contact.linkedin if contact is not None else None,
    )


@router.get("/people/{person_id}", response_model=PersonDetail)
def person_detail(
    person_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.scalar(
        select(Person).where(
            Person.id == person_id, Person.user_id == current_user.id
        )
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )
    return _build_detail(db, current_user.id, person)


@router.patch("/people/{person_id}", response_model=PersonDetail)
def update_person_detail(
    person_id: str,
    payload: PersonPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.scalar(
        select(Person).where(
            Person.id == person_id, Person.user_id == current_user.id
        )
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )
    if payload.title is not None:
        person.title = payload.title
    upsert_contact(
        db,
        current_user.id,
        person_id,
        payload.email,
        payload.phone,
        payload.linkedin,
    )
    db.commit()
    db.refresh(person)
    return _build_detail(db, current_user.id, person)
```

- [ ] **Step 4: Run the contact tests and the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contacts.py -v`
Expected: 5 passed.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 69 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/people.py backend/tests/test_contacts.py
git commit -m "feat: add GET and PATCH person detail endpoints"
```

---

## Task 4: Frontend contact card

**Files:**
- Modify: `frontend/index.html`

Add a detail panel that opens when a person node is clicked, with editable role and contact fields and action buttons. Keep the existing known-through prefill behavior.

- [ ] **Step 1: Add the card markup inside the Map view**

In `frontend/index.html`, inside `#mapView`, right after the `<div id="cy"></div>`, add:
```html
    <div id="personCard" style="display:none">
      <div class="cardhead">
        <strong id="cardName"></strong>
        <button class="taskdel" onclick="closeCard()">close</button>
      </div>
      <div id="cardCompany" class="muted"></div>
      <label class="cardlabel">Role</label>
      <input id="cardTitle" placeholder="e.g. SDE1, Recruiter" />
      <label class="cardlabel">Email</label>
      <input id="cardEmail" placeholder="email" />
      <label class="cardlabel">Phone</label>
      <input id="cardPhone" placeholder="phone" />
      <label class="cardlabel">LinkedIn</label>
      <input id="cardLinkedin" placeholder="linkedin url" />
      <div class="cardactions">
        <button onclick="savePersonCard()">Save</button>
        <button id="cardEmailBtn" class="secondary" onclick="emailPerson()">Email</button>
        <button id="cardLinkedinBtn" class="secondary" onclick="openLinkedin()">LinkedIn</button>
      </div>
      <span id="cardStatus" class="muted"></span>
    </div>
```

- [ ] **Step 2: Add styles inside the `<style>` block**

```css
    #personCard { position: fixed; top: 150px; right: 24px; width: 280px;
                  background: var(--panel); border: 1px solid var(--line);
                  border-radius: 12px; padding: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.45); }
    #personCard input { width: 100%; }
    .cardhead { display: flex; justify-content: space-between; align-items: center; }
    .cardlabel { font-size: 11px; color: var(--muted); display: block; margin-top: 8px; }
    .cardactions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
```

- [ ] **Step 3: Add the card JS in the `<script>` block**

```javascript
    let cardPersonId = null;

    async function openPersonCard(personId) {
      cardPersonId = personId;
      const d = await api("/people/" + personId);
      document.getElementById("cardName").textContent = d.name;
      document.getElementById("cardCompany").textContent = d.company || "";
      document.getElementById("cardTitle").value = d.title || "";
      document.getElementById("cardEmail").value = d.email || "";
      document.getElementById("cardPhone").value = d.phone || "";
      document.getElementById("cardLinkedin").value = d.linkedin || "";
      document.getElementById("cardEmailBtn").style.display = d.email ? "inline-block" : "none";
      document.getElementById("cardLinkedinBtn").style.display = d.linkedin ? "inline-block" : "none";
      document.getElementById("cardStatus").textContent = "";
      document.getElementById("personCard").style.display = "block";
    }

    function closeCard() {
      document.getElementById("personCard").style.display = "none";
      cardPersonId = null;
    }

    async function savePersonCard() {
      if (!cardPersonId) return;
      const body = {
        title: document.getElementById("cardTitle").value,
        email: document.getElementById("cardEmail").value,
        phone: document.getElementById("cardPhone").value,
        linkedin: document.getElementById("cardLinkedin").value,
      };
      document.getElementById("cardStatus").textContent = "Saving...";
      try {
        await api("/people/" + cardPersonId, { method: "PATCH", body: JSON.stringify(body) });
        document.getElementById("cardStatus").textContent = "Saved.";
        openPersonCard(cardPersonId);
      } catch (e) { document.getElementById("cardStatus").textContent = e.message || "Save failed."; }
    }

    function emailPerson() {
      const email = document.getElementById("cardEmail").value.trim();
      if (!email) return;
      window.open("https://mail.google.com/mail/?view=cm&fs=1&to=" + encodeURIComponent(email), "_blank");
    }

    function openLinkedin() {
      let url = document.getElementById("cardLinkedin").value.trim();
      if (!url) return;
      if (url.indexOf("http") !== 0) url = "https://" + url;
      window.open(url, "_blank");
    }
```

- [ ] **Step 4: Open the card on person click**

Find `onNodeClick(params)`. In the branch that handles a person node (id starts with `"person:"`), after the existing known-through prefill line(s), add:
```javascript
        openPersonCard(id.split(":")[1]);
```
Do not change the You-node or company-node branches.

- [ ] **Step 5: Manual check**

Start the app (SQLite), open http://localhost:8000, go to Map, add a person, click them, fill in email/phone/linkedin and a role, Save, reload the card (click again) and confirm the values persist. Click Email and confirm Gmail compose opens addressed to them.

- [ ] **Step 6: Confirm the suite still passes**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 69 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: contact card panel with email and linkedin actions"
```

---

## Task 5: End-to-end verification

**Files:** none.

- [ ] **Step 1: Start the app on a fresh SQLite database in the background**

```
$env:DATABASE_URL = "sqlite:///./kith_p7.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

- [ ] **Step 2: Add a person, patch details, read them back**

```
$reg = Invoke-RestMethod -Uri http://localhost:8000/auth/register -Method Post -ContentType application/json -Body '{"email":"p7@example.com","password":"hunter2"}'
$h = @{ Authorization = "Bearer " + $reg.access_token }
$p = Invoke-RestMethod -Uri http://localhost:8000/people -Method Post -ContentType application/json -Headers $h -Body '{"name":"Dipunj Gupta","company":"Cloudflare"}'
Invoke-RestMethod -Uri "http://localhost:8000/people/$($p.id)" -Method Patch -ContentType application/json -Headers $h -Body '{"title":"SDE1","email":"dipunj@example.com","linkedin":"in/dipunj"}' | Out-Null
Invoke-RestMethod -Uri "http://localhost:8000/people/$($p.id)" -Method Get -Headers $h | ConvertTo-Json -Depth 5
```
Expected: the detail shows name "Dipunj Gupta", company "Cloudflare", title "SDE1", email and linkedin set, phone null.

- [ ] **Step 3: Stop the server. Manual browser confirmation by the user** (click a person, edit, save, Email button opens Gmail compose).

---

## Self-Review

**Spec coverage:** Contact table with no migration (Task 1, new table via create_all); role via `Person.title` plus email/phone/linkedin (Tasks 2 to 3); `GET`/`PATCH /people/{id}` returning the merged card (Task 3); partial patch preserves other fields (Task 2 service + Task 3 test); per-user scoping and auth (tests); frontend detail panel with Email (Gmail compose) and LinkedIn buttons, hidden when empty (Task 4). Deferred items (name/company edit, contacts list view) correctly absent.

**Type consistency:** `get_contact(db, user_id, person_id)` and `upsert_contact(db, user_id, person_id, email, phone, linkedin)` are defined in Task 2 and called in Task 3. `PersonDetail` and `PersonPatch` fields match the router and the frontend body. `_build_detail` returns `PersonDetail`. The frontend PATCH body `{title, email, phone, linkedin}` matches `PersonPatch`.

**Placeholder scan:** No TBDs. Complete code in every step; tests have real assertions and exact counts (64, 66, 69).

**Known pragmatic choices:** contact details live in their own table to avoid an ALTER on `people` (no Alembic yet). PATCH treats a missing field as "leave unchanged" and an empty string as "set to empty". The card is verified manually; the mailto action uses Gmail web compose per the user's request.
