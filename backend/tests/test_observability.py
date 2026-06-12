from app.observability.tracer import NoopTracer, get_tracer


def test_get_tracer_is_noop_without_keys():
    assert isinstance(get_tracer(), NoopTracer)


from app.llm.gemini import GeminiClient
from app.schemas.extraction import ExtractedCompany, ExtractionResult


class _SpyTracer:
    def __init__(self):
        self.calls = []

    def record_extraction(self, input_text, model, output, latency_ms, error=None):
        self.calls.append(
            {"input": input_text, "model": model, "output": output, "error": error}
        )


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeModels:
    def __init__(self, parsed):
        self._parsed = parsed

    def generate_content(self, **kwargs):
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.models = _FakeModels(parsed)


def test_gemini_client_records_a_trace_on_success():
    spy = _SpyTracer()
    expected = ExtractionResult(companies=[ExtractedCompany(name="Stripe")], people=[])
    client = GeminiClient(
        api_key="test", model="gemini-2.5-flash", tracer=spy
    )
    client._client = _FakeClient(expected)

    client.extract_entities("hello")

    assert len(spy.calls) == 1
    assert spy.calls[0]["model"] == "gemini-2.5-flash"
    assert spy.calls[0]["error"] is None
    assert "Stripe" in spy.calls[0]["output"]
