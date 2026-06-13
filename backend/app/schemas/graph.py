from typing import Optional

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    sublabel: Optional[str] = None
    color: Optional[str] = None
    favorite: bool = False


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
