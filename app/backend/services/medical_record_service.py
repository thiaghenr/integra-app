from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.medical_record import MedicalRecord
from app.backend.models.user import User, UserRole
from app.backend.repositories.medical_record_repository import MedicalRecordRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate


class MedicalRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = MedicalRecordRepository(session)
        self.prof_repo = ProfessionalRepository(session)

    async def _professional_id_for_user(self, user: User) -> int | None:
        prof = await self.prof_repo.get_by_user_id(user.id)
        return prof.id if prof else None

    async def list(
        self, clinic_id: int | None, current_user: User, patient_id: int | None = None
    ) -> list[MedicalRecord]:
        professional_id = None
        if current_user.role == UserRole.professional:
            professional_id = await self._professional_id_for_user(current_user)
        return await self.repo.list_by_clinic(clinic_id, professional_id=professional_id, patient_id=patient_id)

    async def get(self, clinic_id: int | None, record_id: int, current_user: User) -> MedicalRecord:
        record = await self.repo.get_by_clinic(clinic_id, record_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        if current_user.role == UserRole.professional:
            own_prof_id = await self._professional_id_for_user(current_user)
            if record.professional_id != own_prof_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return record

    async def create(self, clinic_id: int | None, data: MedicalRecordCreate, current_user: User) -> MedicalRecord:
        professional_id = await self._professional_id_for_user(current_user)
        record = MedicalRecord(
            clinic_id=clinic_id,
            professional_id=professional_id,
            record_date=data.record_date or datetime.utcnow(),
            **{k: v for k, v in data.model_dump().items() if k != "record_date"},
        )
        return await self.repo.create(record)

    async def update(
        self, clinic_id: int | None, record_id: int, data: MedicalRecordUpdate, current_user: User
    ) -> MedicalRecord:
        record = await self.get(clinic_id, record_id, current_user)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(record, field, value)
        record.updated_at = datetime.utcnow()
        return await self.repo.update(record)
