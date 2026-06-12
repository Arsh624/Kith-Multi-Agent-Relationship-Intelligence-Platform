from abc import ABC, abstractmethod

from app.schemas.extraction import ExtractionResult


class LLMClient(ABC):
    @abstractmethod
    def extract_entities(self, text: str) -> ExtractionResult:
        """Extract people and companies from a raw message."""
        raise NotImplementedError
