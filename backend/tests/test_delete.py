def _register(client, email="del@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_company_dedup_is_case_insensitive(client):
    headers = _register(client)
    client.post("/people", headers=headers, json={"name": "Ram", "company": "Stripe"})
    client.post("/people", headers=headers, json={"name": "Sita", "company": "stripe"})

    graph = client.get("/graph", headers=headers).json()
    companies = [n for n in graph["nodes"] if n["type"] == "company"]
    assert len(companies) == 1


def test_delete_person_removes_node_and_connection(client):
    headers = _register(client)
    client.post("/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"})
    created = client.post(
        "/people",
        headers=headers,
        json={"name": "Rahul", "company": "Qualcomm", "known_through": "Dipunj"},
    )
    rahul_id = created.json()["id"]

    response = client.delete(f"/people/{rahul_id}", headers=headers)
    assert response.status_code == 204

    graph = client.get("/graph", headers=headers).json()
    assert not any(n["label"] == "Rahul" for n in graph["nodes"])
    assert not any(
        e["label"] == "KNOWS" and e["target"] == f"person:{rahul_id}"
        for e in graph["edges"]
    )


def test_delete_person_unknown_returns_404(client):
    headers = _register(client)
    response = client.delete("/people/nonexistent", headers=headers)
    assert response.status_code == 404


def test_delete_company_detaches_people(client):
    headers = _register(client)
    client.post("/people", headers=headers, json={"name": "Ram", "company": "Stripe"})

    graph = client.get("/graph", headers=headers).json()
    company_node = next(n for n in graph["nodes"] if n["type"] == "company")
    company_id = company_node["id"].split(":", 1)[1]

    response = client.delete(f"/companies/{company_id}", headers=headers)
    assert response.status_code == 204

    graph = client.get("/graph", headers=headers).json()
    assert not any(n["type"] == "company" for n in graph["nodes"])
    assert any(n["label"] == "Ram" for n in graph["nodes"])
    assert not any(e["label"] == "WORKS_AT" for e in graph["edges"])


def test_delete_requires_auth(client):
    assert client.delete("/people/x").status_code in (401, 403)
    assert client.delete("/companies/x").status_code in (401, 403)
