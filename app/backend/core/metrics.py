"""Prometheus metric definitions, exposed via GET /metrics
(app/routers/metrics.py). Module-level singletons — prometheus_client's
default registry deduplicates by name, so this must only be imported once
per process (importing it twice under different module paths would raise
a duplicate-metric error, same as any other prometheus_client usage).
"""

from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total DB queries executed",
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "DB query duration in seconds",
)

DB_DESTRUCTIVE_STATEMENTS = Counter(
    "db_destructive_statements_total",
    "DROP / TRUNCATE / unfiltered DELETE / DROP COLUMN statements executed — "
    "the metric that would have caught the Aug 8 dev-DB wipe early via an alert.",
)
