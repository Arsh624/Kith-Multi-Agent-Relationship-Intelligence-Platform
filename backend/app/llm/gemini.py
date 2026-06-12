from google import genai
from google.genai import types

from app.llm.base import LLMClient
from app.schemas.extraction import ExtractionResult

EXTRACTION_PROMPT = (
    "You extract professional networking information from a message. "
    "Identify the people mentioned and the companies they are associated with. "
    "For each person, capture their name, their job title if stated, the company "
    "they are associated with if stated, and a short note about anything relevant "
    "they said or offered. List each distinct company by name. Only include "
    "information that is actually present in the message. Do not invent people or "
    "companies.\n\nMessage:\n"
)


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract_entities(self, text: str) -> ExtractionResult:
        response = self._client.models.generate_content(
            model=self._model,
            contents=EXTRACTION_PROMPT + text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractionResult,
            ),
        )
        result = response.parsed
        if result is None:
            return ExtractionResult()
        return result
