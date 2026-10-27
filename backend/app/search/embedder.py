import hashlib
from typing import Protocol, runtime_checkable

# Gemini accepts up to 100 texts per batch embedding request.
_BATCH_SIZE = 100


@runtime_checkable
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        ...


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def embed(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=self._model, contents=text
        )
        return list(result.embeddings[0].values)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            result = self._client.models.embed_content(
                model=self._model, contents=texts[start : start + _BATCH_SIZE]
            )
            vectors.extend(list(e.values) for e in result.embeddings)
        return vectors


class FakeEmbedder:
    DIM = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.DIM
        for word in text.lower().split():
            digest = hashlib.md5(word.encode("utf-8")).hexdigest()
            vector[int(digest, 16) % self.DIM] += 1.0
        return vector

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
