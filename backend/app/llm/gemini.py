import time
from typing import Optional

from google import genai
from google.genai import types

from app.llm.base import LLMClient
from app.llm.errors import LLMUnavailableError
from app.observability.tracer import NoopTracer, Tracer
from app.schemas.extraction import ExtractionResult

EXTRACTION_PROMPT = (
    "You extract professional networking information from a message. "
    "Identify the people mentioned and the companies they are associated with. "
    "For each person, capture their name, their job title if stated, the company "
    "they are associated with if stated, and a short note about anything relevant "
    "they said or offered. List each distinct company by name. "
    "Also capture relationships between people: if one person knows, referred, or "
    "offered to introduce you to another person, record it as a relationship with "
    "from_person, to_person, and relation_type set to one of knows, referred, or "
    "can_intro. Only include information that is actually present in the message. "
    "Do not invent people, companies, or relationships.\n\nMessage:\n"
)


class GeminiClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_models: Optional[list[str]] = None,
        tracer: Optional[Tracer] = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._models = [model] + list(fallback_models or [])
        self._tracer = tracer or NoopTracer()

    def extract_entities(self, text: str) -> ExtractionResult:
        start = time.perf_counter()
        last_error: Optional[Exception] = None
        for model in self._models:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=EXTRACTION_PROMPT + text,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractionResult,
                    ),
                )
                result = response.parsed
                if result is None:
                    result = ExtractionResult()
                latency_ms = (time.perf_counter() - start) * 1000
                self._tracer.record_extraction(
                    text, model, result.model_dump_json(), latency_ms
                )
                return result
            except Exception as exc:  # noqa: BLE001  external API, fall back then surface
                last_error = exc
        latency_ms = (time.perf_counter() - start) * 1000
        self._tracer.record_extraction(
            text, self._models[-1], "", latency_ms, str(last_error)
        )
        raise LLMUnavailableError(str(last_error))
