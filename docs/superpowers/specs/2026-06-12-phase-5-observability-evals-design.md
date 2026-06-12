# Kith Phase 5: Observability and Evals

**Design spec** · 2026-06-12

## Purpose

Make the AI layer debuggable and measurable: trace every extraction so you can see what
the model saw and produced, and score extraction accuracy against a fixed set of known
examples so prompt changes are measured, not guessed.

## Scope

### In scope (Phase 5)
- A small `Tracer` abstraction with a real `LangfuseTracer` (Langfuse Cloud free tier) and
  a `NoopTracer`, selected by whether Langfuse keys are configured. Wired into the
  `GeminiClient` so each extraction records input, the model that answered (including
  fallback), the output, latency, and success or failure.
- An **eval dataset** of curated messages with known-correct extractions, a **scorer**
  that computes precision, recall, and F1 for people, companies, and relationships, and a
  **runner script** that executes the dataset through the real Extractor and prints a
  report.
- Tests: the tracer wiring (a spy tracer asserts the client records a trace) and the scorer
  (precision/recall logic) are hermetic. The full eval run and live Langfuse traces are
  manual, using the real Gemini key.

### Explicitly deferred
- Tracing the whole request graph (just the extraction calls for now).
- Automated eval runs in CI (the runner is a local script first).
- Gmail auto-sync (separate later phase).

## Success criteria
- With Langfuse keys set, pasting a message produces a trace in the Langfuse dashboard
  showing the input text, model used, structured output, and latency.
- With no keys set, everything works exactly as before (the tracer is a no-op); the test
  suite never needs Langfuse.
- `python -m evals.run_evals` prints per-category precision/recall/F1 and an overall score
  against the dataset.
- The scorer is unit-tested and the tracer wiring is unit-tested, hermetically.

## Architecture

### Tracer (`app/observability/tracer.py`)
```
class Tracer(Protocol):
    def record_extraction(self, input_text, model, output, latency_ms, error) -> None
```
- `NoopTracer`: does nothing.
- `LangfuseTracer`: lazily builds a Langfuse client from settings and records one trace per
  extraction (a generation with input, output, model, latency, and a status flag).
- `get_tracer()`: returns `LangfuseTracer` if `settings.langfuse_public_key` and
  `settings.langfuse_secret_key` are set, else `NoopTracer`. Tracer construction never
  raises if keys are missing.

### GeminiClient integration
- `GeminiClient.__init__` gains an optional `tracer` parameter (default `NoopTracer()`).
- `extract_entities` times the call, and after the chosen model returns (or all fail),
  calls `tracer.record_extraction(...)` with the input, the model that answered, the JSON
  output (or empty), the elapsed milliseconds, and any error string. The existing fallback
  behavior is unchanged.
- `get_llm_client` injects `get_tracer()` so production traces and tests stay no-op.

### Config and dependency
- `settings` gains `langfuse_public_key`, `langfuse_secret_key`, `langfuse_host`
  (default `https://cloud.langfuse.com`), all default empty; real values live in
  gitignored `backend/.env`.
- `langfuse` added to `requirements.txt`.

### Evals (`backend/evals/`)
- `cases.py` (or `cases.json`): a list of `EvalCase(text, expected_people, expected_companies,
  expected_relationships)` covering 12 to 15 realistic messages (intros, "X works at Y",
  "A can intro you to B", multi-person threads, and a noise case with no entities).
- `scorer.py`: `score_case(expected, actual) -> CaseScore` and `aggregate(scores) ->
  Report`. Matching is set-based on normalized names: people by lowercased name, companies
  by lowercased name, relationships by the tuple `(from_lower, to_lower, relation_type)`.
  Computes precision, recall, and F1 per category and overall.
- `run_evals.py`: builds a real `GeminiClient` from settings, runs each case, scores, and
  prints a table plus the aggregate. Manual; uses real Gemini quota. Not part of pytest.

### Testing
- `test_observability.py`: a `SpyTracer` records calls; constructing a `GeminiClient` with
  the spy and a fake underlying client, then calling `extract_entities`, asserts the spy
  received one `record_extraction` with the expected model and a non-null output. A second
  test asserts `get_tracer()` returns a `NoopTracer` when keys are empty.
- `test_scorer.py`: feed known expected/actual pairs and assert precision, recall, and F1
  values (for example, a perfect match scores 1.0; a missed person drops recall; an extra
  company drops precision).

## Files (planned)
```
backend/app/observability/__init__.py
backend/app/observability/tracer.py     Tracer, NoopTracer, LangfuseTracer, get_tracer
backend/app/config.py                    langfuse_* settings
backend/app/llm/gemini.py                accept + call tracer
backend/app/deps.py                      inject get_tracer into GeminiClient
backend/evals/__init__.py
backend/evals/cases.py                   EvalCase dataset
backend/evals/scorer.py                  score_case, aggregate
backend/evals/run_evals.py               manual runner
backend/requirements.txt                 add langfuse
backend/tests/test_observability.py
backend/tests/test_scorer.py
README.md                                eval + langfuse run notes
```
