from app.observability.tracer import NoopTracer, get_tracer


def test_get_tracer_is_noop_without_keys():
    assert isinstance(get_tracer(), NoopTracer)
