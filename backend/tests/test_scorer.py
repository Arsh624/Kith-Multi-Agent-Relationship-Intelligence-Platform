from app.schemas.extraction import (
    ExtractedCompany,
    ExtractedPerson,
    ExtractedRelationship,
    ExtractionResult,
)
from evals.cases import EvalCase
from evals.scorer import score_case


def test_perfect_match_scores_one():
    case = EvalCase(text="x", people=["Priya"], companies=["Stripe"])
    actual = ExtractionResult(
        people=[ExtractedPerson(name="priya")],
        companies=[ExtractedCompany(name="stripe")],
    )
    scores = score_case(case, actual)
    assert scores["people"].f1 == 1.0
    assert scores["companies"].f1 == 1.0


def test_missing_person_drops_recall():
    case = EvalCase(text="x", people=["Priya", "Ravi"])
    actual = ExtractionResult(people=[ExtractedPerson(name="Priya")])
    scores = score_case(case, actual)
    assert scores["people"].recall == 0.5


def test_extra_company_drops_precision():
    case = EvalCase(text="x", companies=["Stripe"])
    actual = ExtractionResult(
        companies=[ExtractedCompany(name="Stripe"), ExtractedCompany(name="Extra")]
    )
    scores = score_case(case, actual)
    assert scores["companies"].precision == 0.5


def test_relationship_scoring():
    case = EvalCase(text="x", relationships=[("Dipunj", "Rahul", "knows")])
    actual = ExtractionResult(
        relationships=[
            ExtractedRelationship(
                from_person="dipunj", to_person="rahul", relation_type="knows"
            )
        ]
    )
    scores = score_case(case, actual)
    assert scores["relationships"].f1 == 1.0
