"""Three named loggers (app.api, app.database, app.system), each writing
structured JSON lines to its own rotating file at the repo root plus stdout.

Files are local/dev convenience only — production runs on ECS Fargate with
ephemeral container storage, so stdout (captured by CloudWatch via the
awslogs log driver, see infra/cdk/integra_stack.py) is what actually
persists in prod. Every handler gets the same JSON formatter so both
destinations carry identical structured data.
"""

import json
import logging
import logging.handlers
from datetime import UTC, datetime
from pathlib import Path

from app.backend.core.config import settings
from app.backend.core.tracing import (
    get_current_user_id,
    get_current_user_role,
    get_request_id,
    get_span_id,
    get_trace_id,
)

LOGGER_NAMES = ("app.api", "app.database", "app.system")

# Attributes every stdlib LogRecord carries — anything else on the record
# came from a caller's `extra={...}` and should be surfaced in the JSON body.
_STANDARD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Correlation IDs are pulled from the
    request-scoped contextvars (app.backend.core.tracing), not from the
    LogRecord, so every log call gets them for free without passing extra=
    at every call site.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": get_trace_id(),
            "request_id": get_request_id(),
            "span_id": get_span_id(),
        }
        user_id = get_current_user_id()
        if user_id is not None:
            payload["user_id"] = user_id
            payload["user_role"] = get_current_user_role()

        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def _build_handlers(filename: str) -> list[logging.Handler]:
    log_path = Path(settings.LOG_DIR) / filename
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
    )
    stream_handler = logging.StreamHandler()

    formatter = JsonFormatter()
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    return [file_handler, stream_handler]


def setup_logging() -> None:
    """Idempotent: safe to call on every app/alembic process start (handlers
    are cleared and rebuilt each time), so settings changes like LOG_DIR
    (used by tests) take effect on the next call.
    """
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logger_files = {
        "app.api": "api.log",
        "app.database": "database.log",
        "app.system": "system.log",
    }
    for name, filename in logger_files.items():
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            handler.close()
        logger.handlers.clear()
        logger.setLevel(level)
        logger.propagate = False
        # migrations/env.py calls logging.config.fileConfig() (for
        # alembic.ini's own [loggers]) before this, whose default
        # disable_existing_loggers=True silently disables any logger not
        # listed there — including these three, since they already exist in
        # the registry by then. Undo that explicitly rather than relying on
        # call order.
        logger.disabled = False
        for handler in _build_handlers(filename):
            logger.addHandler(handler)


api_logger = logging.getLogger("app.api")
database_logger = logging.getLogger("app.database")
system_logger = logging.getLogger("app.system")
