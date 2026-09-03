import json
import logging

from app.backend.core.logging_config import JsonFormatter
from app.backend.core.tracing import request_id_var, span_id_var, trace_id_var


def _make_record(message: str = "hello", level: int = logging.INFO, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.api",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_produces_valid_json_with_required_fields():
    record = _make_record("request handled", status_code=200)
    payload = json.loads(JsonFormatter().format(record))

    for field in ("timestamp", "level", "logger", "message", "trace_id", "request_id", "span_id"):
        assert field in payload
    assert payload["message"] == "request handled"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.api"
    assert payload["status_code"] == 200


def test_formatter_includes_exception_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _make_record("failure", level=logging.ERROR)
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))
    assert "exception" in payload
    assert "ValueError: boom" in payload["exception"]


def test_formatter_reads_trace_id_from_contextvar():
    token = trace_id_var.set("trace-123")
    req_token = request_id_var.set("req-456")
    span_token = span_id_var.set("span-789")
    try:
        payload = json.loads(JsonFormatter().format(_make_record()))
    finally:
        trace_id_var.reset(token)
        request_id_var.reset(req_token)
        span_id_var.reset(span_token)

    assert payload["trace_id"] == "trace-123"
    assert payload["request_id"] == "req-456"
    assert payload["span_id"] == "span-789"


def test_formatter_trace_id_is_none_outside_request_context():
    payload = json.loads(JsonFormatter().format(_make_record()))
    assert payload["trace_id"] is None
    assert payload["request_id"] is None
