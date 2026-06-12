import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.llm.errors import LLMUnavailableError
from app.llm.gemini import GeminiClient
from evals.cases import CASES
from evals.scorer import aggregate, score_case

# Gemini free tier allows about 5 requests per minute, so pace the calls.
DELAY_SECONDS = 13


def main() -> None:
    client = GeminiClient(
        api_key=settings.gemini_api_key, model=settings.gemini_model
    )
    scores = []
    for index, case in enumerate(CASES, start=1):
        if index > 1:
            time.sleep(DELAY_SECONDS)
        try:
            actual = client.extract_entities(case.text)
        except LLMUnavailableError as exc:
            print(f"Case {index:2d}: skipped (model unavailable: {exc})")
            continue
        case_scores = score_case(case, actual)
        scores.append(case_scores)
        print(
            f"Case {index:2d}: "
            f"people f1={case_scores['people'].f1:.2f} "
            f"companies f1={case_scores['companies'].f1:.2f} "
            f"rels f1={case_scores['relationships'].f1:.2f}"
        )

    overall = aggregate(scores)
    print(f"\nAggregate over {len(scores)} of {len(CASES)} cases:")
    for category, score in overall.items():
        print(
            f"  {category:14s} precision={score.precision:.2f} "
            f"recall={score.recall:.2f} f1={score.f1:.2f}"
        )


if __name__ == "__main__":
    main()
