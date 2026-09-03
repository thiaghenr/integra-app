import asyncpg
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import every model so SQLModel.metadata knows about all tables before create_all().
import app.backend.models.appointment  # noqa: F401
import app.backend.models.body_signal  # noqa: F401
import app.backend.models.check_in  # noqa: F401
import app.backend.models.check_in_body_signal  # noqa: F401
import app.backend.models.check_in_emotion  # noqa: F401
import app.backend.models.clinic  # noqa: F401
import app.backend.models.emotion  # noqa: F401
import app.backend.models.emotion_diary_entry  # noqa: F401
import app.backend.models.family_member  # noqa: F401
import app.backend.models.goal  # noqa: F401
import app.backend.models.material  # noqa: F401
import app.backend.models.medical_record  # noqa: F401
import app.backend.models.mission  # noqa: F401
import app.backend.models.patient  # noqa: F401
import app.backend.models.phone_list  # noqa: F401
import app.backend.models.professional  # noqa: F401
import app.backend.models.user  # noqa: F401
from app.backend.core.config import settings


def _test_database_url(async_url: str) -> str:
    root, _, dbname = async_url.rpartition("/")
    return f"{root}/{dbname}_test"


TEST_DATABASE_URL = _test_database_url(settings.DATABASE_URL)
_TEST_DB_NAME = TEST_DATABASE_URL.rpartition("/")[2]


def _asyncpg_dsn(async_url: str, dbname: str) -> str:
    # postgresql+asyncpg://user:pass@host:port/dbname -> postgresql://user:pass@host:port/dbname
    plain = async_url.replace("postgresql+asyncpg://", "postgresql://")
    root = plain.rpartition("/")[0]
    return f"{root}/{dbname}"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Creates a fresh test database with all tables, once per test session.

    Runs synchronously (its own throwaway event loop) so it never holds
    asyncpg connections open across test functions, which each get their
    own event loop under pytest-asyncio's default function-scoped mode.
    """
    import asyncio

    async def _setup():
        maintenance_dsn = _asyncpg_dsn(settings.DATABASE_URL, "postgres")
        conn = await asyncpg.connect(maintenance_dsn)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}" WITH (FORCE)')
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
        finally:
            await conn.close()

        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        await engine.dispose()

    asyncio.run(_setup())
    return TEST_DATABASE_URL
