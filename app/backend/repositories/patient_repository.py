from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.phone import phone_variants
from app.backend.models.patient import Patient
from app.backend.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Patient, session)

    async def list_by_clinic(self, clinic_id: int | None, search: str | None = None) -> list[Patient]:
        stmt = select(Patient).where(Patient.is_active == True)  # noqa: E712
        if clinic_id is not None:
            stmt = stmt.where(Patient.clinic_id == clinic_id)
        if search:
            term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Patient.name.ilike(term),
                    Patient.surname.ilike(term),
                    Patient.cpf.ilike(term),
                )
            )
        stmt = stmt.order_by(Patient.name, Patient.surname)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_user_id(self, user_id: int) -> Patient | None:
        result = await self.session.exec(
            select(Patient).where(Patient.user_id == user_id, Patient.is_active == True)  # noqa: E712
        )
        return result.first()

    async def get_by_clinic(self, clinic_id: int | None, patient_id: int) -> Patient | None:
        stmt = select(Patient).where(Patient.id == patient_id)
        if clinic_id is not None:
            stmt = stmt.where(Patient.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_phone(self, clinic_id: int | None, phone: str) -> Patient | None:
        stmt = select(Patient).where(
            Patient.phone.in_(phone_variants(phone)), Patient.is_active == True  # noqa: E712
        )
        if clinic_id is not None:
            stmt = stmt.where(Patient.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_ids(self, clinic_id: int | None, patient_ids: list[int]) -> list[Patient]:
        if not patient_ids:
            return []
        stmt = select(Patient).where(Patient.id.in_(patient_ids), Patient.is_active == True)  # noqa: E712
        if clinic_id is not None:
            stmt = stmt.where(Patient.clinic_id == clinic_id)
        stmt = stmt.order_by(Patient.name, Patient.surname)
        result = await self.session.exec(stmt)
        return list(result.all())
