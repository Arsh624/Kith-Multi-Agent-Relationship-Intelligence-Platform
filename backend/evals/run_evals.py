import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.llm.gemini import GeminiClient
from evals.cases import CASES
from evals.scorer import aggregate, score_case


def main() -> None:
    client = GeminiClient(
        api_key=settings.gemini_api_key, model=settings.gemini_model
    )
    scores = []
    for index, case in enumerate(CASES, start=1):
        actual = client.extract_entities(case.text)
        case_scores = score_case(case, actual)
        scores.append(case_scores)
        print(
            f"Case {index:2d}: "
            f"people f1={case_scores['people'].f1:.2f} "
            f"companies f1={case_scores['companies'].f1:.2f} "
            f"rels f1={case_scores['relationships'].f1:.2f}"
        )

    overall = aggregate(scores)
    print("\nAggregate:")
    for category, score in overall.items():
        print(
            f"  {category:14s} precision={score.precision:.2f} "
            f"recall={score.recall:.2f} f1={score.f1:.2f}"
        )


if __name__ == "__main__":
    main()
