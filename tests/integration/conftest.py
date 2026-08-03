import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.security import hash_password
from app.backend.models.clinic import Clinic
from app.backend.models.patient import Patient
from app.backend.models.professional import Professional
from app.backend.models.user import User, UserRole


@pytest.fixture
async def db_session(test_database):
    # A fresh engine per test avoids asyncpg connections crossing event loops
    # between test functions (pytest-asyncio gives each test its own loop).
    engine = create_async_engine(test_database)
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())

    session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_local() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def clinic(db_session: AsyncSession) -> Clinic:
    c = Clinic(name="Test Clinic", slug="test-clinic")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


async def _make_user(db_session: AsyncSession, clinic: Clinic, role: UserRole, email: str) -> User:
    u = User(
        clinic_id=clinic.id,
        email=email,
        password_hash=hash_password("testpass123"),
        name="Test",
        surname=role.value.capitalize(),
        role=role,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def superadmin_user(db_session: AsyncSession, clinic: Clinic) -> User:
    return await _make_user(db_session, clinic, UserRole.superadmin, "superadmin@test.com")


@pytest.fixture
async def admin_user(db_session: AsyncSession, clinic: Clinic) -> User:
    return await _make_user(db_session, clinic, UserRole.admin, "admin@test.com")


@pytest.fixture
async def professional_user(db_session: AsyncSession, clinic: Clinic) -> User:
    return await _make_user(db_session, clinic, UserRole.professional, "professional@test.com")


@pytest.fixture
async def viewer_user(db_session: AsyncSession, clinic: Clinic) -> User:
    return await _make_user(db_session, clinic, UserRole.viewer, "viewer@test.com")


@pytest.fixture
async def professional(db_session: AsyncSession, clinic: Clinic, professional_user: User) -> Professional:
    p = Professional(
        clinic_id=clinic.id,
        user_id=professional_user.id,
        name="Joana",
        surname="Silva",
        specialization="Psicologia",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def patient_user(db_session: AsyncSession, clinic: Clinic) -> User:
    return await _make_user(db_session, clinic, UserRole.paciente, "patient@test.com")


@pytest.fixture
async def patient(db_session: AsyncSession, clinic: Clinic, patient_user: User) -> Patient:
    p = Patient(clinic_id=clinic.id, user_id=patient_user.id, name="Maria", surname="Souza")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def other_patient(db_session: AsyncSession, clinic: Clinic) -> Patient:
    p = Patient(clinic_id=clinic.id, name="Outro", surname="Paciente")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p
