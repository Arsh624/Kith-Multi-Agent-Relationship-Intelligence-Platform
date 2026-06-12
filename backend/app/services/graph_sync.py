from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.base import (
    GraphSnapshot,
    SnapshotCompany,
    SnapshotConnection,
    SnapshotPerson,
)
from app.models.company import Company
from app.models.connection import Connection
from app.models.person import Person


def build_snapshot(db: Session, user_id: str) -> GraphSnapshot:
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()
    companies = db.scalars(
        select(Company).where(Company.user_id == user_id)
    ).all()
    connections = db.scalars(
        select(Connection).where(Connection.user_id == user_id)
    ).all()

    return GraphSnapshot(
        people=[
            SnapshotPerson(id=p.id, name=p.name, company_id=p.company_id)
            for p in people
        ],
        companies=[SnapshotCompany(id=c.id, name=c.name) for c in companies],
        connections=[
            SnapshotConnection(
                from_person_id=c.from_person_id,
                to_person_id=c.to_person_id,
                relation_type=c.relation_type,
            )
            for c in connections
        ],
    )
