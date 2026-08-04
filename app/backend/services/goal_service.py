from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.goal import Goal
from app.backend.models.patient import Patient
from app.backend.models.user import User, UserRole
from app.backend.repositories.goal_repository import GoalRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.repositories.professional_repository import ProfessionalRepository
from app.backend.schemas.goal import GoalCreate, GoalStatusUpdate, GoalUpdate

_ADMIN_ROLES = (UserRole.superadmin, UserRole.admin)


class GoalService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = GoalRepository(session)
        self.prof_repo = ProfessionalRepository(session)
        self.patient_repo = PatientRepository(session)

    async def _professional_id_for_user(self, user: User) -> int | None:
        prof = await self.prof_repo.get_by_user_id(user.id)
        return prof.id if prof else None

    async def _own_patient(self, current_user: User) -> Patient:
        patient = await self.patient_repo.get_by_user_id(current_user.id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No patient profile linked to this account"
            )
        return patient

    async def list(self, clinic_id: int | None, current_user: User, patient_id: int | None = None) -> list[Goal]:
        if current_user.role in _ADMIN_ROLES:
            return await self.repo.list_by_clinic(clinic_id, patient_id=patient_id)
        if current_user.role == UserRole.professional:
            professional_id = await self._professional_id_for_user(current_user)
            return await self.repo.list_by_clinic(clinic_id, professional_id=professional_id, patient_id=patient_id)
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            if patient_id is not None and patient_id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return await self.repo.list_by_clinic(clinic_id, patient_id=patient.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def get(self, clinic_id: int | None, goal_id: int, current_user: User) -> Goal:
        goal = await self.repo.get_by_clinic(clinic_id, goal_id)
        if not goal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
        if current_user.role in _ADMIN_ROLES:
            return goal
        if current_user.role == UserRole.professional:
            own_prof_id = await self._professional_id_for_user(current_user)
            if goal.professional_id != own_prof_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return goal
        if current_user.role == UserRole.paciente:
            patient = await self._own_patient(current_user)
            if goal.patient_id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return goal
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def create(self, clinic_id: int, data: GoalCreate, current_user: User) -> Goal:
        professional_id = await self._professional_id_for_user(current_user)
        if not professional_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No professional profile linked to this account"
            )
        goal = Goal(clinic_id=clinic_id, professional_id=professional_id, **data.model_dump())
        return await self.repo.create(goal)

    async def update(self, clinic_id: int | None, goal_id: int, data: GoalUpdate, current_user: User) -> Goal:
        goal = await self.get(clinic_id, goal_id, current_user)
        if current_user.role == UserRole.paciente:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(goal, field, value)
        goal.updated_at = datetime.utcnow()
        return await self.repo.update(goal)

    async def update_status(
        self, clinic_id: int | None, goal_id: int, data: GoalStatusUpdate, current_user: User
    ) -> Goal:
        goal = await self.get(clinic_id, goal_id, current_user)
        goal.status = data.status
        goal.updated_at = datetime.utcnow()
        return await self.repo.update(goal)

    async def soft_delete(self, clinic_id: int | None, goal_id: int, current_user: User) -> None:
        goal = await self.get(clinic_id, goal_id, current_user)
        if current_user.role == UserRole.paciente:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        goal.is_active = False
        goal.updated_at = datetime.utcnow()
        await self.repo.update(goal)
