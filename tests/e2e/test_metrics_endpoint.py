"""GET /metrics returns Prometheus-formatted output. Mounted only when
ENV != "prod" (see app/main.py's api() factory) — the test suite runs with
ENV=dev (see .env / tests/conftest.py), so the route should be present.
"""


async def test_metrics_endpoint_returns_prometheus_format(client):
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    body = response.text
    for metric_name in (
        "http_requests_total",
        "http_request_duration_seconds",
        "db_queries_total",
        "db_query_duration_seconds",
        "db_destructive_statements_total",
    ):
        assert metric_name in body, f"{metric_name} missing from /metrics output"


async def test_metrics_reflects_requests_made_through_the_app(client):
    await client.get("/login")
    response = await client.get("/metrics")

    body = response.text
    assert 'http_requests_total{method="GET"' in body
