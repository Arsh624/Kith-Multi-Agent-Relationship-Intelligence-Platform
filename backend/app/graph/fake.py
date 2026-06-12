from collections import deque

from app.graph.base import GraphSnapshot, GraphStore


class FakeGraphStore(GraphStore):
    def __init__(self) -> None:
        self._snapshots: dict[str, GraphSnapshot] = {}

    def sync_user_graph(self, user_id: str, snapshot: GraphSnapshot) -> None:
        self._snapshots[user_id] = snapshot

    def intro_paths(
        self, user_id: str, company_name: str, max_hops: int = 4
    ) -> list[list[str]]:
        snapshot = self._snapshots.get(user_id)
        if snapshot is None:
            return []

        people = {p.id: p for p in snapshot.people}
        company_name_by_id = {c.id: c.name for c in snapshot.companies}
        target = company_name.strip().lower()

        adjacency: dict[str, list[str]] = {}
        incoming: set[str] = set()
        for connection in snapshot.connections:
            adjacency.setdefault(connection.from_person_id, []).append(
                connection.to_person_id
            )
            incoming.add(connection.to_person_id)

        def company_of(person_id: str) -> str:
            person = people.get(person_id)
            if person is None or person.company_id is None:
                return ""
            return (company_name_by_id.get(person.company_id) or "").strip().lower()

        first_degree = [p.id for p in snapshot.people if p.id not in incoming]

        results: list[list[str]] = []
        queue: deque[list[str]] = deque([fid] for fid in first_degree)
        while queue:
            path = queue.popleft()
            current = path[-1]
            if company_of(current) == target:
                company = company_name_by_id.get(people[current].company_id)
                results.append(
                    ["You"] + [people[pid].name for pid in path] + [company]
                )
            if len(path) >= max_hops:
                continue
            for nxt in adjacency.get(current, []):
                if nxt not in path:
                    queue.append(path + [nxt])

        results.sort(key=len)
        return results[:5]
