"""Query-level observability for database.log.

Listens at the sync `Engine` class level (not on one specific engine
instance) so every async engine in the process is covered automatically —
the app's own engine (app.backend.core.database.engine) as well as the
throwaway engines tests/conftest.py and tests/integration/conftest.py create
for the disposable test database.

LIMITATION: this only covers queries issued through SQLAlchemy engines
created in this process. A `DROP DATABASE`, `docker compose down -v`, or any
other command run outside the app (psql, a manual docker command, an
out-of-band script) will not appear here — see CLAUDE.md's Observability
section for what that means for incident diagnosis.
"""

import re
import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.backend.core.logging_config import database_logger
from app.backend.core.metrics import DB_DESTRUCTIVE_STATEMENTS, DB_QUERIES_TOTAL, DB_QUERY_DURATION
from app.backend.core.tracing import current_user_id_var, current_user_role_var, new_id, span_id_var

_DROP_OR_TRUNCATE_RE = re.compile(r"\b(DROP|TRUNCATE)\b", re.IGNORECASE)
_DELETE_RE = re.compile(r"^\s*DELETE\s+FROM\b", re.IGNORECASE)
_WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)


def is_destructive_statement(statement: str) -> bool:
    """Flags DROP (table/database/index/...), TRUNCATE, ALTER TABLE ... DROP
    COLUMN (also caught by the DROP keyword), and DELETE with no WHERE
    clause. Does not flag UPDATE without WHERE — out of scope per spec,
    would be a reasonable follow-up.
    """
    if _DROP_OR_TRUNCATE_RE.search(statement):
        return True
    return bool(_DELETE_RE.search(statement) and not _WHERE_RE.search(statement))


@event.listens_for(Engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    context._integra_query_start = time.perf_counter()
    context._integra_span_token = span_id_var.set(new_id())


@event.listens_for(Engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
    duration_ms = (time.perf_counter() - getattr(context, "_integra_query_start", time.perf_counter())) * 1000
    destructive = is_destructive_statement(statement)

    extra = {
        "statement": statement,
        "duration_ms": round(duration_ms, 2),
        "rowcount": cursor.rowcount,
        "destructive": destructive,
    }

    if destructive:
        DB_DESTRUCTIVE_STATEMENTS.inc()
        database_logger.warning("Destructive statement executed", extra=extra)
    else:
        database_logger.info("Query executed", extra=extra)

    DB_QUERIES_TOTAL.inc()
    DB_QUERY_DURATION.observe(duration_ms / 1000)

    token = getattr(context, "_integra_span_token", None)
    if token is not None:
        span_id_var.reset(token)


def log_query_context(user_id: int | None, user_role: str | None):
    """Small helper for callers (session middleware) that want to attach the
    authenticated user to the current_user contextvars for the duration of a
    request, so destructive-statement log lines can name who issued them.
    Returns the reset tokens; caller is responsible for resetting.
    """
    return current_user_id_var.set(user_id), current_user_role_var.set(user_role)


__all__ = ["is_destructive_statement", "log_query_context"]
