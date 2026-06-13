from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.connection import Connection
from app.models.person import Person
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse

YOU_NODE_ID = "you"


def build_graph(db: Session, user_id: str) -> GraphResponse:
    companies = db.scalars(
        select(Company).where(Company.user_id == user_id)
    ).all()
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()
    connections = db.scalars(
        select(Connection).where(Connection.user_id == user_id)
    ).all()

    introduced = {c.to_person_id for c in connections}

    nodes: list[GraphNode] = [
        GraphNode(id=YOU_NODE_ID, label="You", type="you")
    ]
    edges: list[GraphEdge] = []

    for company in companies:
        nodes.append(
            GraphNode(
                id=f"company:{company.id}",
                label=company.name,
                type="company",
                color=company.color,
            )
        )

    for person in people:
        nodes.append(
            GraphNode(
                id=f"person:{person.id}",
                label=person.name,
                type="person",
                sublabel=person.title,
                color=person.color,
                favorite=bool(person.favorite),
            )
        )
        if person.company_id is not None:
            edges.append(
                GraphEdge(
                    source=f"person:{person.id}",
                    target=f"company:{person.company_id}",
                    label="WORKS_AT",
                )
            )
        if person.id not in introduced:
            edges.append(
                GraphEdge(
                    source=YOU_NODE_ID,
                    target=f"person:{person.id}",
                    label="KNOWS",
                )
            )

    for connection in connections:
        edges.append(
            GraphEdge(
                source=f"person:{connection.from_person_id}",
                target=f"person:{connection.to_person_id}",
                label=connection.relation_type.upper(),
            )
        )

    return GraphResponse(nodes=nodes, edges=edges)
