import pytest
from fastapi import HTTPException

from app.backend.models.user import UserRole
from app.backend.repositories.user_repository import UserRepository
from app.backend.schemas.professional import ProfessionalCreate
from app.backend.services.professional_service import ProfessionalService


async def test_create_without_user_id_auto_creates_account(db_session, clinic):
    service = ProfessionalService(db_session)
    data = ProfessionalCreate(
        name="Carlos",
        surname="Mendes",
        cpf="123.456.789-00",
        specialization="Fisioterapia",
        email="carlos@test.com",
    )

    professional, generated_password = await service.create(clinic.id, data)

    assert generated_password is not None
    assert professional.user_id is not None
    linked_user = await UserRepository(db_session).get(professional.user_id)
    assert linked_user is not None
    assert linked_user.role == UserRole.professional
    assert linked_user.force_password_change is True


async def test_create_without_user_id_and_without_email_fails(db_session, clinic):
    service = ProfessionalService(db_session)
    data = ProfessionalCreate(name="Carlos", surname="Mendes", cpf="123.456.789-00", specialization="Fisioterapia")

    with pytest.raises(HTTPException) as exc_info:
        await service.create(clinic.id, data)

    assert exc_info.value.status_code == 400


async def test_create_with_existing_user_id_does_not_generate_password(db_session, clinic, professional_user):
    service = ProfessionalService(db_session)
    data = ProfessionalCreate(
        name="Carlos",
        surname="Mendes",
        cpf="123.456.789-00",
        specialization="Fisioterapia",
        user_id=professional_user.id,
    )

    professional, generated_password = await service.create(clinic.id, data)

    assert generated_password is None
    assert professional.user_id == professional_user.id
