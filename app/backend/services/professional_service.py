from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.patient import Patient
from app.backend.models.professional import Professional
from app.backend.models.user import UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.professional import ProfessionalCreate, ProfessionalUpdate
from app.backend.schemas.user import UserCreate
from app.backend.services.user_service import UserService


class ProfessionalService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ProfessionalRepository(session)
        self.user_service = UserService(session)
        self.appointment_repo = AppointmentRepository(session)
        self.patient_repo = PatientRepository(session)

    async def list(self, clinic_id: int | None, active_only: bool = True) -> list[Professional]:
        return await self.repo.list_by_clinic(clinic_id, active_only=active_only)

    async def get(self, clinic_id: int | None, professional_id: int) -> Professional:
        prof = await self.repo.get(professional_id)
        if not prof or (clinic_id is not None and prof.clinic_id != clinic_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
        return prof

    async def create(self, clinic_id: int, data: ProfessionalCreate) -> tuple[Professional, str | None]:
        user_id = data.user_id
        generated_password = None
        if user_id is None:
            if not data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="E-mail é obrigatório para criar a conta de usuário do profissional",
                )
            generated_password = secrets.token_urlsafe(9)
            user = await self.user_service.create(
                clinic_id,
                UserCreate(
                    email=data.email,
                    name=data.name,
                    surname=data.surname,
                    role=UserRole.professional,
                    password=generated_password,
                    phone=data.phone,
                ),
                force_password_change=True,
            )
            user_id = user.id

        prof = Professional(clinic_id=clinic_id, **data.model_dump(exclude={"user_id"}), user_id=user_id)
        prof = await self.repo.create(prof)
        return prof, generated_password

    async def update(self, clinic_id: int | None, professional_id: int, data: ProfessionalUpdate) -> Professional:
        prof = await self.get(clinic_id, professional_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(prof, field, value)
        return await self.repo.update(prof)

    async def soft_delete(self, clinic_id: int | None, professional_id: int) -> None:
        prof = await self.get(clinic_id, professional_id)
        prof.is_active = False
        await self.repo.update(prof)

    async def list_patients(self, clinic_id: int | None, professional_id: int) -> list[Patient]:
        appointments = await self.appointment_repo.list_by_clinic(clinic_id, professional_id=professional_id)
        patient_ids = sorted({a.patient_id for a in appointments})
        return await self.patient_repo.get_by_ids(clinic_id, patient_ids)
