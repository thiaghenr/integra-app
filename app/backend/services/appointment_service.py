from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.appointment import Appointment, AppointmentStatus
from app.backend.models.user import User, UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.appointment import AppointmentCreate, AppointmentUpdate


class AppointmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AppointmentRepository(session)
        self.prof_repo = ProfessionalRepository(session)

    async def _professional_id_for_user(self, user: User) -> int | None:
        prof = await self.prof_repo.get_by_user_id(user.id)
        return prof.id if prof else None

    async def list(
        self, clinic_id: int | None, current_user: User, professional_id: int | None = None
    ) -> list[Appointment]:
        if current_user.role == UserRole.professional:
            professional_id = await self._professional_id_for_user(current_user)
        return await self.repo.list_by_clinic(clinic_id, professional_id=professional_id)

    async def list_today(self, clinic_id: int | None) -> list[Appointment]:
        return await self.repo.list_today(clinic_id)

    async def get(self, clinic_id: int | None, appointment_id: int, current_user: User) -> Appointment:
        appt = await self.repo.get_by_clinic(clinic_id, appointment_id)
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
        if current_user.role == UserRole.professional:
            own_prof_id = await self._professional_id_for_user(current_user)
            if appt.professional_id != own_prof_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return appt

    async def create(self, clinic_id: int | None, data: AppointmentCreate, current_user: User) -> Appointment:
        appt = Appointment(
            clinic_id=clinic_id,
            created_by=current_user.id,
            **data.model_dump(),
        )
        return await self.repo.create(appt)

    async def update(
        self, clinic_id: int | None, appointment_id: int, data: AppointmentUpdate, current_user: User
    ) -> Appointment:
        appt = await self.get(clinic_id, appointment_id, current_user)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(appt, field, value)
        appt.updated_at = datetime.utcnow()
        return await self.repo.update(appt)

    async def cancel(self, clinic_id: int | None, appointment_id: int, current_user: User) -> Appointment:
        appt = await self.get(clinic_id, appointment_id, current_user)
        appt.status = AppointmentStatus.cancelled
        appt.updated_at = datetime.utcnow()
        return await self.repo.update(appt)

    async def count_by_status(self, clinic_id: int | None) -> dict[str, int]:
        return await self.repo.count_by_status(clinic_id)
