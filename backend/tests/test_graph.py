from app.deps import get_llm_client
from app.main import app
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractionResult,
)
from tests.fakes import FakeLLMClient


def _register(client, email="u@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "hunter2"}
    )
    return response.json()["access_token"]


def test_graph_returns_nodes_and_edges_after_paste(client):
    token = _register(client)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(
                    name="Priya Sharma", title="PM", company="Stripe", note="x"
                )
            ],
        )
    )
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        client.post(
            "/paste",
            headers={"Authorization": f"Bearer {token}"},
            json={"source": "email", "text": "Priya is a PM at Stripe."},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    response = client.get(
        "/graph", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()

    labels = {n["label"]: n["type"] for n in body["nodes"]}
    assert labels.get("Stripe") == "company"
    assert labels.get("Priya Sharma") == "person"

    person_id = next(
        n["id"] for n in body["nodes"] if n["label"] == "Priya Sharma"
    )
    company_id = next(
        n["id"] for n in body["nodes"] if n["label"] == "Stripe"
    )
    assert any(
        e["source"] == person_id
        and e["target"] == company_id
        and e["label"] == "WORKS_AT"
        for e in body["edges"]
    )


def test_graph_requires_auth(client):
    response = client.get("/graph")
    assert response.status_code in (401, 403)


def test_graph_empty_for_new_user(client):
    token = _register(client)
    response = client.get(
        "/graph", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 1
    assert body["nodes"][0]["id"] == "you"
    assert body["nodes"][0]["type"] == "you"
    assert body["edges"] == []
