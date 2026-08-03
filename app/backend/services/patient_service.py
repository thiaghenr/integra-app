import secrets
from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.patient import Patient
from app.backend.models.user import UserRole
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.patient import PatientCreate, PatientUpdate
from app.backend.schemas.user import UserCreate
from app.backend.services.user_service import UserService


class PatientService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = PatientRepository(session)
        self.user_service = UserService(session)

    async def list(self, clinic_id: int | None, search: str | None = None) -> list[Patient]:
        return await self.repo.list_by_clinic(clinic_id, search=search)

    async def get(self, clinic_id: int | None, patient_id: int) -> Patient:
        patient = await self.repo.get_by_clinic(clinic_id, patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        return patient

    async def create(self, clinic_id: int, data: PatientCreate) -> tuple[Patient, str | None]:
        user_id = data.user_id
        generated_password = None
        if user_id is None:
            if not data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="E-mail é obrigatório para criar a conta de usuário do paciente",
                )
            generated_password = secrets.token_urlsafe(9)
            user = await self.user_service.create(
                clinic_id,
                UserCreate(
                    email=data.email,
                    name=data.name,
                    surname=data.surname,
                    role=UserRole.paciente,
                    password=generated_password,
                    phone=data.phone,
                ),
                force_password_change=True,
            )
            user_id = user.id

        patient = Patient(clinic_id=clinic_id, **data.model_dump(exclude={"user_id"}), user_id=user_id)
        patient = await self.repo.create(patient)
        return patient, generated_password

    async def update(self, clinic_id: int | None, patient_id: int, data: PatientUpdate) -> Patient:
        patient = await self.get(clinic_id, patient_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(patient, field, value)
        patient.updated_at = datetime.utcnow()
        return await self.repo.update(patient)

    async def soft_delete(self, clinic_id: int | None, patient_id: int) -> None:
        patient = await self.get(clinic_id, patient_id)
        patient.is_active = False
        patient.updated_at = datetime.utcnow()
        await self.repo.update(patient)
