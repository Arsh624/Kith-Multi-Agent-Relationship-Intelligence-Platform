from app.graph.base import GraphSnapshot, GraphStore
from app.services.intro_paths import compute_intro_paths


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
        return compute_intro_paths(snapshot, company_name, max_hops)
