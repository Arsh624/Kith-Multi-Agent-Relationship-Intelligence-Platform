import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.llm.gemini import GeminiClient

SAMPLE = (
    "Hey, great chatting earlier. I am a PM at Stripe. My friend Ravi leads "
    "recruiting at Notion, you two should connect. Ping me next week and I will "
    "introduce you."
)


def main() -> None:
    client = GeminiClient(
        api_key=settings.gemini_api_key, model=settings.gemini_model
    )
    result = client.extract_entities(SAMPLE)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
