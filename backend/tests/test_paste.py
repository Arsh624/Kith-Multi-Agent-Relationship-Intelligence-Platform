from app.deps import get_llm_client
from app.main import app
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractionResult,
)
from tests.fakes import FakeLLMClient


def _auth_token(client):
    response = client.post(
        "/auth/register",
        json={"email": "u@example.com", "password": "hunter2"},
    )
    return response.json()["access_token"]


def test_paste_extracts_and_persists(client):
    token = _auth_token(client)
    fake = FakeLLMClient(
        ExtractionResult(
            companies=[ExtractedCompany(name="Stripe")],
            people=[
                ExtractedPerson(
                    name="Priya Sharma",
                    title="PM",
                    company="Stripe",
                    note="offered intro",
                )
            ],
        )
    )
    app.dependency_overrides[get_llm_client] = lambda: fake
    try:
        response = client.post(
            "/paste",
            headers={"Authorization": f"Bearer {token}"},
            json={"source": "email", "text": "Priya is a PM at Stripe."},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 201
    body = response.json()
    assert body["message_id"]
    assert len(body["companies"]) == 1
    assert body["companies"][0]["name"] == "Stripe"
    assert len(body["people"]) == 1
    assert body["people"][0]["name"] == "Priya Sharma"
    assert body["people"][0]["company"] == "Stripe"
    assert body["people"][0]["note"] == "offered intro"


def test_paste_requires_auth(client):
    response = client.post(
        "/paste", json={"source": "email", "text": "hello"}
    )
    assert response.status_code in (401, 403)


class _UnavailableLLM:
    def extract_entities(self, text):
        from app.llm.errors import LLMUnavailableError

        raise LLMUnavailableError("overloaded")


def test_paste_returns_503_when_model_unavailable(client):
    token = _auth_token(client)
    app.dependency_overrides[get_llm_client] = lambda: _UnavailableLLM()
    try:
        response = client.post(
            "/paste",
            headers={"Authorization": f"Bearer {token}"},
            json={"source": "email", "text": "anything"},
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 503
    assert "busy" in response.json()["detail"].lower()
