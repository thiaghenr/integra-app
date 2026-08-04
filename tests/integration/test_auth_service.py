import pytest
from fastapi import HTTPException

from app.backend.models.phone_list import PhoneList
from app.backend.services.auth_service import AuthService


@pytest.fixture
async def user_with_phone(db_session, patient_user):
    from app.backend.core.phone import canonical_phone

    phone = "5545991115537"
    db_session.add(PhoneList(user_id=patient_user.id, phone=phone, phone_canonical=canonical_phone(phone)))
    await db_session.commit()
    return patient_user


async def test_authenticate_by_phone_matches_nine_digit_variant(db_session, user_with_phone):
    service = AuthService(db_session)

    found = await service.authenticate_by_phone("5545991115537")

    assert found.id == user_with_phone.id


async def test_authenticate_by_phone_matches_missing_nine_digit_variant(db_session, user_with_phone):
    service = AuthService(db_session)

    found = await service.authenticate_by_phone("554591115537")

    assert found.id == user_with_phone.id


async def test_authenticate_by_phone_unknown_number_raises_404(db_session, user_with_phone):
    service = AuthService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.authenticate_by_phone("5511900000000")

    assert exc_info.value.status_code == 404
