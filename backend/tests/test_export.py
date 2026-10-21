def _register(client, email="exp@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_export_returns_all_user_data(client):
    headers = _register(client)
    dipunj = client.post(
        "/people", headers=headers, json={"name": "Dipunj", "company": "Cloudflare"}
    ).json()
    client.post(
        "/people",
        headers=headers,
        json={"name": "Rahul", "company": "Qualcomm", "known_through": "Dipunj"},
    )
    client.patch(
        f"/people/{dipunj['id']}",
        headers=headers,
        json={"note": "referral asked", "status": "hot", "email": "d@x.com"},
    )
    client.post("/tasks", headers=headers, json={"title": "Follow up", "priority": "high"})

    data = client.get("/export", headers=headers).json()

    assert "exported_at" in data
    names = {p["name"] for p in data["people"]}
    assert names == {"Dipunj", "Rahul"}
    dipunj_row = next(p for p in data["people"] if p["name"] == "Dipunj")
    assert dipunj_row["company"] == "Cloudflare"
    assert dipunj_row["note"] == "referral asked"
    assert dipunj_row["status"] == "hot"
    assert dipunj_row["email"] == "d@x.com"
    assert {c["name"] for c in data["companies"]} == {"Cloudflare", "Qualcomm"}
    assert len(data["connections"]) == 1
    assert data["tasks"][0]["title"] == "Follow up"


def test_export_is_scoped_to_user(client):
    headers_a = _register(client, "a@example.com")
    headers_b = _register(client, "b@example.com")
    client.post("/people", headers=headers_a, json={"name": "OnlyMine"})

    data_b = client.get("/export", headers=headers_b).json()
    assert data_b["people"] == []


def test_export_requires_auth(client):
    assert client.get("/export").status_code in (401, 403)
