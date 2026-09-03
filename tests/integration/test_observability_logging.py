"""Issues a real request through the app and asserts that api.log,
database.log, and system.log all record an entry carrying the same
trace_id — the property the whole tracing design exists to guarantee (a
single request can be reconstructed across all three files by grepping one
ID). Uses a route that authenticates (so session_middleware's user lookup
produces a database.log line) and then raises (so the unhandled-exception
handler produces a system.log line), alongside the api.log line every
request produces.
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.main as main_module
from app.backend.core.deps import get_db
from app.backend.core.security import create_session_token
from app.backend.models.clinic import Clinic
from app.backend.models.user import User, UserRole


def _read_log_entries(path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


@pytest.fixture
async def observability_client(test_database, monkeypatch, tmp_path):
    monkeypatch.setattr(main_module.settings, "LOG_DIR", str(tmp_path))

    engine = create_async_engine(test_database)
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())

    test_session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(main_module, "AsyncSessionLocal", test_session_local)

    app = main_module.api()

    @app.get("/__test_boom")
    async def boom():  # noqa: ANN202
        raise RuntimeError("boom for observability test")

    async def override_get_db():
        async with test_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with test_session_local() as session:
        clinic = Clinic(name="Obs Clinic", slug="obs-clinic")
        session.add(clinic)
        await session.commit()
        await session.refresh(clinic)

        user = User(
            clinic_id=clinic.id,
            email="obs@test.com",
            password_hash="unused",
            name="Obs",
            surname="User",
            role=UserRole.admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # raise_app_exceptions=False: our route deliberately raises to exercise the
    # unhandled-exception -> system.log path. Starlette's ServerErrorMiddleware
    # always re-raises after building the 500 response (so uvicorn can log it
    # server-side); without this, httpx's ASGITransport re-raises that into the
    # test instead of returning the response that was actually sent.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set(main_module.settings.SESSION_COOKIE_NAME, create_session_token(user.id))
        yield ac, tmp_path

    await engine.dispose()


async def test_request_correlates_across_all_three_log_files(observability_client):
    client, log_dir = observability_client

    response = await client.get("/__test_boom")

    assert response.status_code == 500
    trace_id = response.headers.get("X-Trace-Id")
    assert trace_id

    api_entries = _read_log_entries(log_dir / "api.log")
    database_entries = _read_log_entries(log_dir / "database.log")
    system_entries = _read_log_entries(log_dir / "system.log")

    assert any(e.get("trace_id") == trace_id for e in api_entries), api_entries
    assert any(e.get("trace_id") == trace_id for e in database_entries), database_entries
    assert any(e.get("trace_id") == trace_id for e in system_entries), system_entries

    # The api.log line for the 500 should be at ERROR, not swallowed as INFO.
    api_line = next(e for e in api_entries if e.get("trace_id") == trace_id)
    assert api_line["level"] == "ERROR"
    assert api_line["status_code"] == 500

    # The system.log line should carry the actual traceback, per spec.
    system_line = next(e for e in system_entries if e.get("trace_id") == trace_id)
    assert "RuntimeError" in system_line.get("exception", "")


async def test_response_includes_trace_id_header(observability_client):
    client, _ = observability_client
    response = await client.get("/__test_boom")
    assert response.headers.get("X-Trace-Id")


async def test_inbound_trace_id_header_is_reused(observability_client):
    client, log_dir = observability_client
    inbound = "11111111-1111-4111-8111-111111111111"

    response = await client.get("/__test_boom", headers={"X-Trace-Id": inbound})

    assert response.headers["X-Trace-Id"] == inbound
    api_entries = _read_log_entries(log_dir / "api.log")
    assert any(e.get("trace_id") == inbound for e in api_entries)
