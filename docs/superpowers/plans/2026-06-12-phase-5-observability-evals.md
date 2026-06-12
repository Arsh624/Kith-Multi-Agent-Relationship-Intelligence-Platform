# Kith Phase 5: Observability and Evals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trace every extraction through a Langfuse-or-noop tracer wired into the GeminiClient, and add an eval dataset plus a precision/recall scorer and runner so extraction quality is measured.

**Architecture:** A tiny `Tracer` protocol with a `NoopTracer` (default) and a `LangfuseTracer` selected only when keys are configured; the GeminiClient records one trace per extraction. A separate `evals/` package holds a curated dataset, a set-based scorer, and a manual runner. Tracing and evals never affect the request path and the test suite stays hermetic (no Langfuse, no real Gemini).

**Tech Stack:** FastAPI, Gemini, Langfuse (v2), pytest. Builds on Phases 0 to 4.

---

## Context for the implementer

Phases 0 to 4 are complete (55 passing tests). Relevant existing code:
- `app/llm/gemini.py`: `GeminiClient(api_key, model, fallback_models=None)`, `extract_entities(text)` loops over models, returns `ExtractionResult`, raises `LLMUnavailableError` if all fail. Constant `EXTRACTION_PROMPT`.
- `app/llm/base.py` (`LLMClient`), `app/llm/errors.py` (`LLMUnavailableError`).
- `app/config.py`: pydantic-settings `Settings` with gemini and neo4j fields.
- `app/deps.py`: `get_llm_client()` builds `GeminiClient` from settings (model + fallback).
- `app/schemas/extraction.py`: `ExtractedCompany`, `ExtractedPerson`, `ExtractedRelationship(from_person, to_person, relation_type, note)`, `ExtractionResult(companies, people, relationships)`.
- `tests/conftest.py` sets env vars before importing app, and has `client` and `db_session` fixtures.
- Run from the `backend` directory: `.\.venv\Scripts\python.exe -m pytest -q`.

No em dashes or en dashes anywhere (code, comments, commit messages).

## File Structure (Phase 5)

```
backend/app/observability/__init__.py     NEW empty
backend/app/observability/tracer.py       NEW Tracer protocol, NoopTracer, LangfuseTracer, get_tracer
backend/app/config.py                      MODIFY langfuse_* settings
backend/tests/conftest.py                  MODIFY clear langfuse env so get_tracer is deterministic
backend/app/llm/gemini.py                  MODIFY accept + call tracer, time the call
backend/app/deps.py                        MODIFY inject get_tracer() into GeminiClient
backend/requirements.txt                   MODIFY add langfuse
backend/evals/__init__.py                  NEW empty
backend/evals/cases.py                     NEW EvalCase + CASES dataset
backend/evals/scorer.py                    NEW CategoryScore, score_case, aggregate
backend/evals/run_evals.py                 NEW manual runner
backend/tests/test_observability.py        NEW tracer wiring tests
backend/tests/test_scorer.py               NEW scorer tests
README.md                                  MODIFY eval + langfuse notes
```

---

## Task 1: Tracer abstraction, config, and dependency

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/observability/__init__.py` (empty)
- Create: `backend/app/observability/tracer.py`
- Test: `backend/tests/test_observability.py` (the `get_tracer` half)

- [ ] **Step 1: Add the langfuse dependency and install it**

Append to `backend/requirements.txt`:
```text
langfuse>=2.50,<3
```
Install: `.\.venv\Scripts\python.exe -m pip install "langfuse>=2.50,<3"`
Then pin the exact version installed: run `.\.venv\Scripts\python.exe -m pip show langfuse` and replace the line in `requirements.txt` with `langfuse==X.Y.Z`.

- [ ] **Step 2: Add Langfuse settings to `backend/app/config.py`**

Add three fields after the neo4j fields (place them with the other settings, before `settings = Settings()`):
```python
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
```

- [ ] **Step 3: Clear Langfuse env in `backend/tests/conftest.py`**

In the top block of `os.environ[...]` assignments (before `import pytest`), add:
```python
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
```
This keeps `get_tracer()` deterministic (always NoopTracer in tests) regardless of `.env`.

- [ ] **Step 4: Create `backend/app/observability/__init__.py`** (empty file)

- [ ] **Step 5: Create `backend/app/observability/tracer.py`**

```python
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
            # tracing is best effort and must never break extraction
            return None


def get_tracer() -> Tracer:
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        return LangfuseTracer(
            settings.langfuse_public_key,
            settings.langfuse_secret_key,
            settings.langfuse_host,
        )
    return NoopTracer()
```

- [ ] **Step 6: Write the failing test `backend/tests/test_observability.py`**

```python
from app.observability.tracer import NoopTracer, get_tracer


def test_get_tracer_is_noop_without_keys():
    assert isinstance(get_tracer(), NoopTracer)
```

- [ ] **Step 7: Run it and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_observability.py -v`
Expected: 1 passed (conftest clears the keys, so `get_tracer` returns `NoopTracer`).

- [ ] **Step 8: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 56 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/tests/conftest.py backend/app/observability/ backend/tests/test_observability.py
git commit -m "feat: add tracer abstraction with langfuse and noop backends"
```

---

## Task 2: Wire the tracer into the GeminiClient (TDD)

**Files:**
- Modify: `backend/app/llm/gemini.py`
- Modify: `backend/app/deps.py`
- Test: `backend/tests/test_observability.py`

- [ ] **Step 1: Add the failing test to `backend/tests/test_observability.py`**

Append:
```python
from app.llm.gemini import GeminiClient
from app.schemas.extraction import ExtractedCompany, ExtractionResult


class _SpyTracer:
    def __init__(self):
        self.calls = []

    def record_extraction(self, input_text, model, output, latency_ms, error=None):
        self.calls.append(
            {"input": input_text, "model": model, "output": output, "error": error}
        )


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeModels:
    def __init__(self, parsed):
        self._parsed = parsed

    def generate_content(self, **kwargs):
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.models = _FakeModels(parsed)


def test_gemini_client_records_a_trace_on_success():
    spy = _SpyTracer()
    expected = ExtractionResult(companies=[ExtractedCompany(name="Stripe")], people=[])
    client = GeminiClient(
        api_key="test", model="gemini-2.5-flash", tracer=spy
    )
    client._client = _FakeClient(expected)

    client.extract_entities("hello")

    assert len(spy.calls) == 1
    assert spy.calls[0]["model"] == "gemini-2.5-flash"
    assert spy.calls[0]["error"] is None
    assert "Stripe" in spy.calls[0]["output"]
```

- [ ] **Step 2: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_observability.py::test_gemini_client_records_a_trace_on_success -v`
Expected: fails because `GeminiClient.__init__` does not accept `tracer` yet.

- [ ] **Step 3: Update `backend/app/llm/gemini.py`**

Add imports at the top (below the existing imports):
```python
import time

from app.observability.tracer import NoopTracer, Tracer
```
Change `__init__` to accept a tracer (keep the rest):
```python
    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_models: Optional[list[str]] = None,
        tracer: Optional[Tracer] = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._models = [model] + list(fallback_models or [])
        self._tracer = tracer or NoopTracer()
```
Replace `extract_entities` with a timed, traced version:
```python
    def extract_entities(self, text: str) -> ExtractionResult:
        start = time.perf_counter()
        last_error: Optional[Exception] = None
        for model in self._models:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=EXTRACTION_PROMPT + text,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ExtractionResult,
                    ),
                )
                result = response.parsed
                if result is None:
                    result = ExtractionResult()
                latency_ms = (time.perf_counter() - start) * 1000
                self._tracer.record_extraction(
                    text, model, result.model_dump_json(), latency_ms
                )
                return result
            except Exception as exc:  # noqa: BLE001  external API, fall back then surface
                last_error = exc
        latency_ms = (time.perf_counter() - start) * 1000
        self._tracer.record_extraction(
            text, self._models[-1], "", latency_ms, str(last_error)
        )
        raise LLMUnavailableError(str(last_error))
```

- [ ] **Step 4: Run the observability tests and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_observability.py -v`
Expected: 2 passed.

- [ ] **Step 5: Inject the tracer in `backend/app/deps.py`**

Add the import and pass `get_tracer()` into the client. Update `get_llm_client`:
```python
from app.observability.tracer import get_tracer
```
```python
def get_llm_client() -> LLMClient:
    fallbacks = (
        [settings.gemini_fallback_model] if settings.gemini_fallback_model else []
    )
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        fallback_models=fallbacks,
        tracer=get_tracer(),
    )
```

- [ ] **Step 6: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 57 passed. The existing GeminiClient tests still pass because the tracer defaults to a no-op and the return values are unchanged.

- [ ] **Step 7: Commit**

```bash
git add backend/app/llm/gemini.py backend/app/deps.py backend/tests/test_observability.py
git commit -m "feat: trace each extraction through the injected tracer"
```

---

## Task 3: Eval scorer (TDD)

**Files:**
- Create: `backend/evals/__init__.py` (empty)
- Create: `backend/evals/cases.py` (the `EvalCase` type only for now)
- Create: `backend/evals/scorer.py`
- Test: `backend/tests/test_scorer.py`

- [ ] **Step 1: Create `backend/evals/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/evals/cases.py` with the type (dataset added in Task 4)**

```python
from dataclasses import dataclass, field


@dataclass
class EvalCase:
    text: str
    people: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    relationships: list[tuple[str, str, str]] = field(default_factory=list)


CASES: list[EvalCase] = []
```

- [ ] **Step 3: Write the failing test `backend/tests/test_scorer.py`**

```python
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
```

- [ ] **Step 4: Run and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scorer.py -v`
Expected: import error (`evals.scorer` does not exist).

- [ ] **Step 5: Create `backend/evals/scorer.py`**

```python
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
```

- [ ] **Step 6: Run and confirm pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scorer.py -v`
Expected: 4 passed.

- [ ] **Step 7: Run the whole suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 61 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/evals/__init__.py backend/evals/cases.py backend/evals/scorer.py backend/tests/test_scorer.py
git commit -m "feat: add eval scorer with precision recall and f1"
```

---

## Task 4: Eval dataset and runner

**Files:**
- Modify: `backend/evals/cases.py` (fill in `CASES`)
- Create: `backend/evals/run_evals.py`

- [ ] **Step 1: Fill in `CASES` in `backend/evals/cases.py`**

Replace `CASES: list[EvalCase] = []` with a curated list (keep the `EvalCase` dataclass above it):
```python
CASES: list[EvalCase] = [
    EvalCase(
        text="Hi, I am a PM at Stripe. Reach out anytime.",
        people=["I"],
        companies=["Stripe"],
    ),
    EvalCase(
        text="Met Priya Sharma today, she is a designer at Figma.",
        people=["Priya Sharma"],
        companies=["Figma"],
    ),
    EvalCase(
        text="My friend Ravi leads recruiting at Notion, I can introduce you.",
        people=["Ravi"],
        companies=["Notion"],
        relationships=[("I", "Ravi", "can_intro")],
    ),
    EvalCase(
        text="Dipunj works at Cloudflare. His friend Rahul is an SDE at Qualcomm.",
        people=["Dipunj", "Rahul"],
        companies=["Cloudflare", "Qualcomm"],
        relationships=[("Dipunj", "Rahul", "knows")],
    ),
    EvalCase(
        text="Sarah referred me to Tom, who runs data at Databricks.",
        people=["Sarah", "Tom"],
        companies=["Databricks"],
        relationships=[("Sarah", "Tom", "referred")],
    ),
    EvalCase(
        text="Thanks for the coffee. No work talk, just catching up.",
        people=[],
        companies=[],
    ),
    EvalCase(
        text="Alex is a founder at a stealth startup, no company name yet.",
        people=["Alex"],
        companies=[],
    ),
    EvalCase(
        text="I chatted with Maya Chen (Google) and Arjun Patel (Stripe) at the meetup.",
        people=["Maya Chen", "Arjun Patel"],
        companies=["Google", "Stripe"],
    ),
    EvalCase(
        text="Priya can connect you with her colleague Neha at Stripe.",
        people=["Priya", "Neha"],
        companies=["Stripe"],
        relationships=[("Priya", "Neha", "can_intro")],
    ),
    EvalCase(
        text="Following up: Ben from Airbnb said to email him next week.",
        people=["Ben"],
        companies=["Airbnb"],
    ),
    EvalCase(
        text="Lena is a recruiter at Meta and knows Sam, a PM at Meta.",
        people=["Lena", "Sam"],
        companies=["Meta"],
        relationships=[("Lena", "Sam", "knows")],
    ),
    EvalCase(
        text="Quick note to self: call the dentist tomorrow.",
        people=[],
        companies=[],
    ),
]
```
Note: the scorer matches on lowercased names, so casing in expectations does not matter. Self references like "I" are included to reflect how the model labels the sender; if the live model omits them, that simply lowers recall on that case, which is fine for a baseline.

- [ ] **Step 2: Create `backend/evals/run_evals.py`**

```python
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
```

- [ ] **Step 3: Confirm the dataset imports and the suite still passes**

Run: `.\.venv\Scripts\python.exe -c "from evals.cases import CASES; print(len(CASES), 'cases')"`
Expected: prints `12 cases`.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 61 passed (no new tests; the runner is manual).

- [ ] **Step 4: Commit**

```bash
git add backend/evals/cases.py backend/evals/run_evals.py
git commit -m "chore: add eval dataset and manual runner"
```

---

## Task 5: Docs and manual verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add an "Observability and evals" section to `README.md`**

Append:
```markdown
## Observability and evals

Extraction is traced through a tracer that is a no-op unless Langfuse keys are set.
To enable Langfuse Cloud (free), add to `backend/.env`:

    LANGFUSE_PUBLIC_KEY=pk-...
    LANGFUSE_SECRET_KEY=sk-...
    LANGFUSE_HOST=https://cloud.langfuse.com

With keys set, each paste creates a trace in the Langfuse dashboard.

Run the extraction evals (uses the real Gemini key, costs a little quota):

    cd backend
    .\.venv\Scripts\python.exe -m evals.run_evals

This prints per-case and aggregate precision, recall, and F1 for people, companies,
and relationships.
```

- [ ] **Step 2: Manual eval run (real Gemini)**

From the `backend` directory: `.\.venv\Scripts\python.exe -m evals.run_evals`
Expected: a per-case table and an aggregate block. Exact numbers vary with the live model;
a healthy baseline has people and companies F1 well above 0.5.

- [ ] **Step 3: Manual Langfuse check (only once keys are available)**

When the user provides Langfuse keys in `backend/.env`, run the app, paste a message, and
confirm a trace appears in the Langfuse dashboard. This is deferred until keys exist; the
no-op path needs no action.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: how to run evals and enable langfuse"
```

---

## Self-Review

**Spec coverage:** Tracer abstraction (Noop + Langfuse) selected by keys: Task 1. GeminiClient records a trace per extraction with model, output, latency, error: Task 2. Eval dataset, scorer (precision/recall/F1 per category), runner: Tasks 3 and 4. Tracer wiring and scorer tested hermetically: Tasks 1 to 3. Langfuse live trace and full eval run are manual: Task 5. Deferred items (full-graph tracing, CI, Gmail) correctly absent.

**Type consistency:** `Tracer.record_extraction(input_text, model, output, latency_ms, error)` is defined in Task 1 and called in Task 2's `GeminiClient` and asserted by the spy in Task 2. `score_case(case, actual) -> dict[str, CategoryScore]` and `aggregate(list) -> dict[str, CategoryScore]` are defined in Task 3 and used by the runner in Task 4 with matching shapes. `EvalCase(text, people, companies, relationships)` is defined in Task 3 and populated in Task 4. `CategoryScore(precision, recall, f1)` field names match across scorer, tests, and runner.

**Placeholder scan:** No TBDs. Every code step is complete; every test has real assertions and exact expected counts (56, 57, 61).

**Known pragmatic choices:** Langfuse pinned to v2 for a stable `.trace()` API; the tracer swallows Langfuse errors so observability never breaks extraction. Eval matching is set-based on normalized names (semantic match is out of scope). The runner and live Langfuse trace are manual, mirroring the existing smoke-test pattern.
