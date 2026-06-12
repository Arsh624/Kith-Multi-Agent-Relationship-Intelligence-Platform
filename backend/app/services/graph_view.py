from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.person import Person
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse


def build_graph(db: Session, user_id: str) -> GraphResponse:
    companies = db.scalars(
        select(Company).where(Company.user_id == user_id)
    ).all()
    people = db.scalars(select(Person).where(Person.user_id == user_id)).all()

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for company in companies:
        nodes.append(
            GraphNode(id=f"company:{company.id}", label=company.name, type="company")
        )

    for person in people:
        nodes.append(
            GraphNode(id=f"person:{person.id}", label=person.name, type="person")
        )
        if person.company_id is not None:
            edges.append(
                GraphEdge(
                    source=f"person:{person.id}",
                    target=f"company:{person.company_id}",
                    label="WORKS_AT",
                )
            )

    return GraphResponse(nodes=nodes, edges=edges)
