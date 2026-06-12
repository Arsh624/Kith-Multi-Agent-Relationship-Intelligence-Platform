import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.graph.base import (
    GraphSnapshot,
    SnapshotCompany,
    SnapshotConnection,
    SnapshotPerson,
)
from app.graph.neo4j_store import Neo4jGraphStore

USER = "smoke-test-user"


def main() -> None:
    store = Neo4jGraphStore(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    snapshot = GraphSnapshot(
        people=[
            SnapshotPerson(id="d", name="Dipunj", company_id="cf"),
            SnapshotPerson(id="r", name="Rahul", company_id="qc"),
        ],
        companies=[
            SnapshotCompany(id="cf", name="Cloudflare"),
            SnapshotCompany(id="qc", name="Qualcomm"),
        ],
        connections=[
            SnapshotConnection(from_person_id="d", to_person_id="r", relation_type="knows")
        ],
    )
    store.sync_user_graph(USER, snapshot)
    print("intro paths to Qualcomm:", store.intro_paths(USER, "Qualcomm"))
    store.close()


if __name__ == "__main__":
    main()
