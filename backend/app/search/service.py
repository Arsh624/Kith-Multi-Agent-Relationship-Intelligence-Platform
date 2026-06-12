from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.person import Person
from app.search.embedder import Embedder
from app.search.store import VectorStore


def _profile_text(name: str, title, company, note) -> str:
    parts = [name, title or "", company or "", note or ""]
    return ". ".join(p for p in parts if p)


def reindex_people(
    db: Session, user_id: str, embedder: Embedder, store: VectorStore
) -> int:
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()
    for person in people:
        company_name = None
        if person.company_id is not None:
            company = db.get(Company, person.company_id)
            company_name = company.name if company is not None else None
        text = _profile_text(
            person.name, person.title, company_name, person.note
        )
        store.index(user_id, person.id, embedder.embed(text))
    return len(people)


def search_people(
    db: Session,
    user_id: str,
    query: str,
    embedder: Embedder,
    store: VectorStore,
    limit: int = 10,
) -> list[dict]:
    hits = store.search(user_id, embedder.embed(query), limit)
    results = []
    for hit in hits:
        person = db.scalar(
            select(Person).where(
                Person.id == hit.person_id, Person.user_id == user_id
            )
        )
        if person is None:
            continue
        company_name = None
        if person.company_id is not None:
            company = db.get(Company, person.company_id)
            company_name = company.name if company is not None else None
        results.append(
            {
                "id": person.id,
                "name": person.name,
                "title": person.title,
                "company": company_name,
                "score": hit.score,
            }
        )
    return results
