from app.llm.base import LLMClient
from app.schemas.extraction import ExtractionResult


class FakeLLMClient(LLMClient):
    def __init__(self, result: ExtractionResult) -> None:
        self._result = result

    def extract_entities(self, text: str) -> ExtractionResult:
        return self._result
