import asyncio

from app.backend.core.tracing import get_span_id, get_trace_id, new_id, span_id_var, trace_id_var


def test_new_id_generates_unique_uuid4_strings():
    a, b = new_id(), new_id()
    assert a != b
    assert len(a) == 36  # UUID4 string form


def test_trace_id_defaults_to_none():
    assert get_trace_id() is None


def test_trace_id_visible_after_set_and_gone_after_reset():
    token = trace_id_var.set("abc-123")
    try:
        assert get_trace_id() == "abc-123"
    finally:
        trace_id_var.reset(token)
    assert get_trace_id() is None


async def test_trace_id_propagates_into_child_asyncio_task():
    # A new asyncio.Task copies the creating context, so a trace_id set
    # before spawning the task must still be visible from inside it —
    # this is exactly what has to hold for request-scoped IDs to reach
    # service/repository code called from a route handler's task.
    token = trace_id_var.set("propagated-trace")
    try:
        seen = await asyncio.create_task(_read_trace_id())
    finally:
        trace_id_var.reset(token)
    assert seen == "propagated-trace"


async def _read_trace_id() -> str | None:
    return get_trace_id()


def test_span_id_independent_of_trace_id():
    trace_token = trace_id_var.set("trace-x")
    span_token = span_id_var.set("span-y")
    try:
        assert get_trace_id() == "trace-x"
        assert get_span_id() == "span-y"
    finally:
        trace_id_var.reset(trace_token)
        span_id_var.reset(span_token)
