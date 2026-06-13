def _register(client, email="style@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_patch_person_color_and_favorite(client):
    headers = _register(client)
    created = client.post(
        "/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"}
    )
    person_id = created.json()["id"]

    patched = client.patch(
        f"/people/{person_id}",
        headers=headers,
        json={"color": "#ff8800", "favorite": True},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["color"] == "#ff8800"
    assert body["favorite"] is True

    graph = client.get("/graph", headers=headers).json()
    node = next(n for n in graph["nodes"] if n["label"] == "Dipunj")
    assert node["color"] == "#ff8800"
    assert node["favorite"] is True


def test_patch_company_color(client):
    headers = _register(client)
    client.post(
        "/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"}
    )
    graph = client.get("/graph", headers=headers).json()
    company_node = next(n for n in graph["nodes"] if n["type"] == "company")
    company_id = company_node["id"].split(":", 1)[1]

    patched = client.patch(
        f"/companies/{company_id}", headers=headers, json={"color": "#445566"}
    )
    assert patched.status_code == 200
    assert patched.json()["color"] == "#445566"

    graph = client.get("/graph", headers=headers).json()
    node = next(n for n in graph["nodes"] if n["id"] == company_node["id"])
    assert node["color"] == "#445566"


def test_person_defaults_have_no_color_and_not_favorite(client):
    headers = _register(client)
    client.post("/people", headers=headers, json={"name": "Plain"})
    graph = client.get("/graph", headers=headers).json()
    node = next(n for n in graph["nodes"] if n["label"] == "Plain")
    assert node["color"] is None
    assert node["favorite"] is False
