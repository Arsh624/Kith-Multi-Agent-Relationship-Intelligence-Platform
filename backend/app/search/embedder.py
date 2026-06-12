import hashlib
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
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


class FakeEmbedder:
    DIM = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.DIM
        for word in text.lower().split():
            digest = hashlib.md5(word.encode("utf-8")).hexdigest()
            vector[int(digest, 16) % self.DIM] += 1.0
        return vector
