import pytest

from app.llm.errors import LLMUnavailableError
from app.llm.gemini import GeminiClient
from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractionResult,
)


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeModels:
    def __init__(self, parsed):
        self._parsed = parsed
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.models = _FakeModels(parsed)


def test_gemini_client_returns_parsed_result():
    expected = ExtractionResult(
        companies=[ExtractedCompany(name="Stripe")],
        people=[
            ExtractedPerson(
                name="Priya", title="PM", company="Stripe", note="offered intro"
            )
        ],
    )
    client = GeminiClient(api_key="test", model="gemini-2.5-flash")
    client._client = _FakeClient(expected)

    result = client.extract_entities("some email text")

    assert result == expected
    assert client._client.models.last_kwargs["model"] == "gemini-2.5-flash"


def test_gemini_client_handles_none_parsed():
    client = GeminiClient(api_key="test", model="gemini-2.5-flash")
    client._client = _FakeClient(None)

    result = client.extract_entities("text")

    assert result == ExtractionResult()


class _FlakyModels:
    def __init__(self, fail_models, parsed):
        self._fail_models = set(fail_models)
        self._parsed = parsed
        self.tried = []

    def generate_content(self, **kwargs):
        model = kwargs["model"]
        self.tried.append(model)
        if model in self._fail_models:
            raise RuntimeError("model overloaded")
        return _FakeResponse(self._parsed)


class _FlakyClient:
    def __init__(self, models):
        self.models = models


def test_gemini_client_falls_back_to_next_model_on_error():
    expected = ExtractionResult(
        companies=[ExtractedCompany(name="Stripe")], people=[]
    )
    client = GeminiClient(
        api_key="test", model="primary", fallback_models=["backup"]
    )
    client._client = _FlakyClient(_FlakyModels(["primary"], expected))

    result = client.extract_entities("text")

    assert result == expected
    assert client._client.models.tried == ["primary", "backup"]


def test_gemini_client_raises_when_all_models_fail():
    client = GeminiClient(
        api_key="test", model="primary", fallback_models=["backup"]
    )
    client._client = _FlakyClient(_FlakyModels(["primary", "backup"], None))

    with pytest.raises(LLMUnavailableError):
        client.extract_entities("text")
