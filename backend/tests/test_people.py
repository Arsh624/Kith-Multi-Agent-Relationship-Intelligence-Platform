def _register(client, email="u@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return response.json()["access_token"]


def test_add_person_with_company_appears_in_graph(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/people", headers=headers, json={"name": "Dana", "company": "Acme"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Dana"
    assert body["company"] == "Acme"

    graph = client.get("/graph", headers=headers).json()
    labels = {n["label"]: n["type"] for n in graph["nodes"]}
    assert labels["Dana"] == "person"
    assert labels["Acme"] == "company"


def test_add_person_without_company(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/people", headers=headers, json={"name": "Solo"})
    assert response.status_code == 201
    assert response.json()["company"] is None

    graph = client.get("/graph", headers=headers).json()
    assert any(n["label"] == "Solo" for n in graph["nodes"])
    assert not any(e["label"] == "WORKS_AT" for e in graph["edges"])
    assert any(
        e["source"] == "you" and e["label"] == "KNOWS" for e in graph["edges"]
    )


def test_add_person_requires_auth(client):
    response = client.post("/people", json={"name": "Nope"})
    assert response.status_code in (401, 403)


def test_list_people_returns_all_with_company_and_favorite(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/people", headers=headers, json={"name": "Dana", "company": "Acme"}
    ).json()
    client.post("/people", headers=headers, json={"name": "Solo"})
    client.patch(
        f"/people/{created['id']}", headers=headers, json={"favorite": True}
    )

    people = client.get("/people", headers=headers).json()
    assert {p["name"] for p in people} == {"Dana", "Solo"}
    by_name = {p["name"]: p for p in people}
    assert by_name["Dana"]["company"] == "Acme"
    assert by_name["Dana"]["favorite"] is True
    assert by_name["Solo"]["company"] is None
    assert by_name["Solo"]["favorite"] is False


def test_list_people_is_scoped_to_user(client):
    headers_a = {"Authorization": f"Bearer {_register(client, 'a@example.com')}"}
    headers_b = {"Authorization": f"Bearer {_register(client, 'b@example.com')}"}
    client.post("/people", headers=headers_a, json={"name": "OnlyMine"})

    people_b = client.get("/people", headers=headers_b).json()
    assert people_b == []


def test_list_people_requires_auth(client):
    response = client.get("/people")
    assert response.status_code in (401, 403)


def test_reorder_people_persists_manual_order(client):
    headers = {"Authorization": f"Bearer {_register(client, 'ro@example.com')}"}
    ids = [
        client.post("/people", headers=headers, json={"name": n}).json()["id"]
        for n in ("Charlie", "Alice", "Bob")
    ]
    new_order = [ids[2], ids[0], ids[1]]

    reordered = client.post(
        "/people/reorder", headers=headers, json={"ids": new_order}
    )
    assert reordered.status_code == 200
    assert [p["id"] for p in reordered.json()] == new_order

    listed = client.get("/people", headers=headers).json()
    assert [p["id"] for p in listed] == new_order
