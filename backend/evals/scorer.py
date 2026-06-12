from dataclasses import dataclass

from app.schemas.extraction import ExtractionResult
from evals.cases import EvalCase


@dataclass
class CategoryScore:
    precision: float
    recall: float
    f1: float


def _prf(expected: set, actual: set) -> CategoryScore:
    if not expected and not actual:
        return CategoryScore(1.0, 1.0, 1.0)
    true_positives = len(expected & actual)
    precision = true_positives / len(actual) if actual else 0.0
    recall = true_positives / len(expected) if expected else 1.0
    denom = precision + recall
    f1 = (2 * precision * recall / denom) if denom else 0.0
    return CategoryScore(precision, recall, f1)


def _names(values) -> set:
    return {v.strip().lower() for v in values}


def score_case(case: EvalCase, actual: ExtractionResult) -> dict[str, CategoryScore]:
    expected_people = _names(case.people)
    actual_people = _names(p.name for p in actual.people)

    expected_companies = _names(case.companies)
    actual_companies = _names(c.name for c in actual.companies)

    expected_rels = {
        (a.strip().lower(), b.strip().lower(), r.strip().lower())
        for (a, b, r) in case.relationships
    }
    actual_rels = {
        (
            rel.from_person.strip().lower(),
            rel.to_person.strip().lower(),
            rel.relation_type.strip().lower(),
        )
        for rel in actual.relationships
    }

    return {
        "people": _prf(expected_people, actual_people),
        "companies": _prf(expected_companies, actual_companies),
        "relationships": _prf(expected_rels, actual_rels),
    }


def aggregate(scores: list[dict[str, CategoryScore]]) -> dict[str, CategoryScore]:
    categories = ["people", "companies", "relationships"]
    result: dict[str, CategoryScore] = {}
    for category in categories:
        if not scores:
            result[category] = CategoryScore(0.0, 0.0, 0.0)
            continue
        precision = sum(s[category].precision for s in scores) / len(scores)
        recall = sum(s[category].recall for s in scores) / len(scores)
        f1 = sum(s[category].f1 for s in scores) / len(scores)
        result[category] = CategoryScore(precision, recall, f1)
    return result
