# Kith Phase 7: Contact Cards

**Design spec** · 2026-06-12

## Purpose

Make each person a useful contact card: store their role/designation and their email,
phone, and LinkedIn, and give one-click actions to email them (opens Gmail compose) or
open their LinkedIn. Click a person in the graph to see and edit their card.

## Scope

### In scope (Phase 7)
- Store contact details for a person: email, phone, LinkedIn. The role/designation reuses
  the existing free-text `Person.title` (so "SDE1", "Recruiter", "Hiring Manager" all fit).
- `GET /people/{id}` returns the full card (name, title, company, note, email, phone,
  linkedin). `PATCH /people/{id}` updates the title and contact fields.
- Frontend: clicking a person node opens a detail panel showing and editing role, email,
  phone, and LinkedIn, with a Save button, an Email button (opens Gmail compose addressed
  to them), and a LinkedIn button (opens their profile). No AI, no Gemini.

### Explicitly deferred
- Editing a person's name or company from the card (kept simple for now).
- A separate contacts list view (the graph is the entry point).
- Logging interactions or reminders tied to a contact.

## Success criteria
- Click a person, see their card; fill in email/phone/linkedin and a role, Save, and the
  values persist (reload shows them).
- The Email button opens Gmail compose pre-addressed to the saved email; the LinkedIn
  button opens the saved profile URL. Both are disabled or hidden when the value is empty.
- Contact data is scoped per user and covered by hermetic tests.
- No database migration is required (the new data lives in a new table, which
  `create_all` adds automatically, so existing local databases keep working).

## Architecture

### Data model (Postgres)
- New table `contacts` (one row per person, created by `create_all` so no migration is
  needed): `id`, `user_id` (FK users), `person_id` (FK people, unique), `email`
  (nullable), `phone` (nullable), `linkedin` (nullable), `created_at`.
- `Person.title` continues to hold the role/designation (already exists).

### Service (`app/services/contacts.py`)
- `get_contact(db, user_id, person_id) -> Contact | None`.
- `upsert_contact(db, user_id, person_id, email, phone, linkedin) -> Contact`: create the
  row if absent, otherwise update only the provided fields.

### Schemas (`app/schemas/people.py` additions)
- `PersonDetail(id, name, title, company, note, email, phone, linkedin)`.
- `PersonPatch(title: Optional[str], email: Optional[str], phone: Optional[str],
  linkedin: Optional[str])` (all optional; only provided fields are updated).

### Router (`app/routers/people.py` additions)
- `GET /people/{person_id}` -> `PersonDetail`, 404 if not found or not owned.
- `PATCH /people/{person_id}` body `PersonPatch` -> `PersonDetail`. Updates `Person.title`
  when provided and upserts the contact row, then returns the full card.

### Frontend (`frontend/index.html`)
- Clicking a person node fetches `GET /people/{id}` and opens a detail panel (a simple
  card in the Map view) with: name and company (read-only), an editable role input, and
  editable email, phone, and LinkedIn inputs; a Save button (`PATCH`); an Email button
  that opens `https://mail.google.com/mail/?view=cm&fs=1&to=EMAIL` in a new tab; and a
  LinkedIn button that opens the saved URL. Buttons are hidden when their value is empty.
  Clicking the You node or a company node does not open the card.
- The existing click behavior (prefill known-through for adding a connected person) is kept
  as the secondary action; the card is the primary thing a person click now shows.

## Testing
- `contacts` service: `upsert_contact` creates then updates only provided fields; scoped
  per user.
- `GET /people/{id}`: returns name/title/company plus contact fields; 404 for unknown or
  another user's person; auth required.
- `PATCH /people/{id}`: sets title and contact fields; a second patch with only some
  fields leaves the others intact; returns the merged card; auth required.
- Hermetic (SQLite, `client`/`db_session` fixtures). The detail panel and mailto/LinkedIn
  buttons are verified manually.

## Files (planned)
```
backend/app/models/contact.py         Contact ORM
backend/app/models/__init__.py        register Contact
backend/app/services/contacts.py      get_contact, upsert_contact
backend/app/schemas/people.py         PersonDetail, PersonPatch
backend/app/routers/people.py         GET + PATCH /people/{id}
frontend/index.html                   detail panel + Email/LinkedIn buttons
backend/tests/test_contacts.py        hermetic tests
```
