from app.graph.base import GraphSnapshot, GraphStore

_ALLOWED_RELATIONS = {"KNOWS", "REFERRED", "CAN_INTRO"}


class Neo4jGraphStore(GraphStore):
    def __init__(
        self, uri: str, username: str, password: str, database: str = ""
    ) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        self._database = database or None

    def close(self) -> None:
        self._driver.close()

    def sync_user_graph(self, user_id: str, snapshot: GraphSnapshot) -> None:
        incoming = {c.to_person_id for c in snapshot.connections}
        with self._driver.session(database=self._database) as session:
            session.execute_write(self._rebuild, user_id, snapshot, incoming)

    @staticmethod
    def _rebuild(tx, user_id, snapshot, incoming):
        tx.run(
            "MATCH (n) WHERE n.user_id = $uid "
            "AND (n:You OR n:Person OR n:Company) DETACH DELETE n",
            uid=user_id,
        )
        tx.run("MERGE (y:You {user_id: $uid}) SET y.name = 'You'", uid=user_id)
        for company in snapshot.companies:
            tx.run(
                "CREATE (c:Company {id: $id, name: $name, user_id: $uid})",
                id=company.id,
                name=company.name,
                uid=user_id,
            )
        for person in snapshot.people:
            tx.run(
                "CREATE (p:Person {id: $id, name: $name, user_id: $uid})",
                id=person.id,
                name=person.name,
                uid=user_id,
            )
            if person.company_id:
                tx.run(
                    "MATCH (p:Person {id: $pid, user_id: $uid}), "
                    "(c:Company {id: $cid, user_id: $uid}) "
                    "CREATE (p)-[:WORKS_AT]->(c)",
                    pid=person.id,
                    cid=person.company_id,
                    uid=user_id,
                )
            if person.id not in incoming:
                tx.run(
                    "MATCH (y:You {user_id: $uid}), "
                    "(p:Person {id: $pid, user_id: $uid}) "
                    "CREATE (y)-[:KNOWS]->(p)",
                    uid=user_id,
                    pid=person.id,
                )
        for connection in snapshot.connections:
            rel = connection.relation_type.upper()
            if rel not in _ALLOWED_RELATIONS:
                rel = "KNOWS"
            tx.run(
                "MATCH (a:Person {id: $f, user_id: $uid}), "
                "(b:Person {id: $t, user_id: $uid}) "
                f"CREATE (a)-[:{rel}]->(b)",
                f=connection.from_person_id,
                t=connection.to_person_id,
                uid=user_id,
            )

    def intro_paths(self, user_id, company_name, max_hops=4):
        query = (
            "MATCH path = (y:You {user_id: $uid})"
            "-[:KNOWS|REFERRED|CAN_INTRO*1..%d]->(p:Person)"
            "-[:WORKS_AT]->(c:Company) "
            "WHERE c.user_id = $uid AND toLower(c.name) = toLower($company) "
            "RETURN [n IN nodes(path) | n.name] AS names "
            "ORDER BY length(path) LIMIT 5" % int(max_hops)
        )
        with self._driver.session(database=self._database) as session:
            result = session.run(query, uid=user_id, company=company_name)
            return [record["names"] for record in result]
