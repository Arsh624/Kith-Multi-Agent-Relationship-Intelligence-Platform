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
    assert graph["edges"] == []


def test_add_person_requires_auth(client):
    response = client.post("/people", json={"name": "Nope"})
    assert response.status_code in (401, 403)
