import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.main as main_module
from app.backend.core.deps import get_db
from app.backend.core.security import hash_password
from app.backend.models.clinic import Clinic
from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole


@pytest.fixture
async def client(test_database, monkeypatch):
    # A fresh engine per test avoids asyncpg connections crossing event loops
    # between test functions (pytest-asyncio gives each test its own loop).
    engine = create_async_engine(test_database)
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())

    test_session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # The auth middleware in app.main opens its own sessions directly (not via Depends),
    # so it must be repointed at the test database explicitly.
    monkeypatch.setattr(main_module, "AsyncSessionLocal", test_session_local)

    app = main_module.api()

    async def override_get_db():
        async with test_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()


@pytest.fixture
async def e2e_clinic(client) -> Clinic:
    # login() hardcodes the "integra-clinic" slug, so e2e fixtures must match it.
    async with main_module.AsyncSessionLocal() as session:
        c = Clinic(name="Integra Clinic", slug="integra-clinic")
        session.add(c)
        await session.commit()
        await session.refresh(c)
        return c


@pytest.fixture
async def e2e_patient_login(client, e2e_clinic) -> dict:
    async with main_module.AsyncSessionLocal() as session:
        user = User(
            clinic_id=e2e_clinic.id,
            email="patient@e2e.test",
            password_hash=hash_password("testpass123"),
            name="Maria",
            surname="Souza",
            role=UserRole.paciente,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        patient = Patient(clinic_id=e2e_clinic.id, user_id=user.id, name="Maria", surname="Souza")
        session.add(patient)
        await session.commit()
        await session.refresh(patient)

    return {"email": "patient@e2e.test", "password": "testpass123", "user": user, "patient": patient}
