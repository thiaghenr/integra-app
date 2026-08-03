import pytest
from fastapi import HTTPException

from app.backend.models.user import UserRole
from app.backend.schemas.user import UserCreate
from app.backend.services.user_service import UserService


async def test_create_user_with_phone_creates_phone_list_entry(db_session, clinic):
    service = UserService(db_session)
    data = UserCreate(
        email="new@test.com", name="New", surname="User", role=UserRole.viewer,
        password="testpass123", phone="45991115537",
    )

    user = await service.create(clinic.id, data)

    from app.backend.repositories.user_repository import UserRepository
    found = await UserRepository(db_session).get_by_phone("5545991115537")
    assert found is not None
    assert found.id == user.id


async def test_create_user_duplicate_email_conflicts(db_session, clinic):
    service = UserService(db_session)
    data = UserCreate(
        email="dup@test.com", name="A", surname="B", role=UserRole.viewer, password="testpass123",
    )
    await service.create(clinic.id, data)

    with pytest.raises(HTTPException) as exc_info:
        await service.create(clinic.id, data)

    assert exc_info.value.status_code == 409


async def test_create_user_duplicate_phone_conflicts_even_with_different_nine_digit_variant(db_session, clinic):
    service = UserService(db_session)
    await service.create(
        clinic.id,
        UserCreate(
            email="first@test.com", name="A", surname="B", role=UserRole.viewer,
            password="testpass123", phone="5545991115537",
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create(
            clinic.id,
            UserCreate(
                email="second@test.com", name="C", surname="D", role=UserRole.viewer,
                password="testpass123", phone="554591115537",
            ),
        )

    assert exc_info.value.status_code == 409
