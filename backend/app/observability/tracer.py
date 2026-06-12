from typing import Optional, Protocol, runtime_checkable

from app.config import settings


@runtime_checkable
class Tracer(Protocol):
    def record_extraction(
        self,
        input_text: str,
        model: str,
        output: str,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> None:
        ...


class NoopTracer:
    def record_extraction(
        self,
        input_text: str,
        model: str,
        output: str,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> None:
        return None


class LangfuseTracer:
    def __init__(self, public_key: str, secret_key: str, host: str) -> None:
        from langfuse import Langfuse

        self._client = Langfuse(
            public_key=public_key, secret_key=secret_key, host=host
        )

    def record_extraction(
        self,
        input_text: str,
        model: str,
        output: str,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> None:
        try:
            self._client.trace(
                name="extract_entities",
                input=input_text,
                output=output,
                metadata={
                    "model": model,
                    "latency_ms": latency_ms,
                    "error": error,
                },
            )
        except Exception:
            return None


def get_tracer() -> Tracer:
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        return LangfuseTracer(
            settings.langfuse_public_key,
            settings.langfuse_secret_key,
            settings.langfuse_host,
        )
    return NoopTracer()
