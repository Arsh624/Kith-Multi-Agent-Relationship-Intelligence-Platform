from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connection import Connection


def add_connection(
    db: Session,
    user_id: str,
    from_person_id: str,
    to_person_id: str,
    relation_type: str = "knows",
    note: Optional[str] = None,
    source_message_id: Optional[str] = None,
) -> Connection:
    existing = db.scalar(
        select(Connection).where(
            Connection.user_id == user_id,
            Connection.from_person_id == from_person_id,
            Connection.to_person_id == to_person_id,
            Connection.relation_type == relation_type,
        )
    )
    if existing is not None:
        return existing
    connection = Connection(
        user_id=user_id,
        from_person_id=from_person_id,
        to_person_id=to_person_id,
        relation_type=relation_type,
        note=note,
        source_message_id=source_message_id,
    )
    db.add(connection)
    db.flush()
    return connection
