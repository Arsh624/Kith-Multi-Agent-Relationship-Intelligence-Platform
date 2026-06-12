from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SnapshotPerson:
    id: str
    name: str
    company_id: Optional[str]


@dataclass
class SnapshotCompany:
    id: str
    name: str


@dataclass
class SnapshotConnection:
    from_person_id: str
    to_person_id: str
    relation_type: str


@dataclass
class GraphSnapshot:
    people: list[SnapshotPerson] = field(default_factory=list)
    companies: list[SnapshotCompany] = field(default_factory=list)
    connections: list[SnapshotConnection] = field(default_factory=list)


class GraphStore(ABC):
    @abstractmethod
    def sync_user_graph(self, user_id: str, snapshot: GraphSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def intro_paths(
        self, user_id: str, company_name: str, max_hops: int = 4
    ) -> list[list[str]]:
        raise NotImplementedError
