from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.family_member import FamilyMember
from app.backend.repositories.family_member_repository import FamilyMemberRepository
from app.backend.repositories.patient_repository import PatientRepository
from app.backend.schemas.family_member import FamilyMemberCreate, FamilyMemberUpdate


class FamilyMemberService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = FamilyMemberRepository(session)
        self.patient_repo = PatientRepository(session)

    async def list(self, clinic_id: int | None, patient_id: int | None = None) -> list[FamilyMember]:
        return await self.repo.list_by_clinic(clinic_id, patient_id=patient_id)

    async def get(self, clinic_id: int | None, family_member_id: int) -> FamilyMember:
        family_member = await self.repo.get_by_clinic(clinic_id, family_member_id)
        if not family_member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family member not found")
        return family_member

    async def create(self, clinic_id: int, data: FamilyMemberCreate) -> FamilyMember:
        patient = await self.patient_repo.get_by_clinic(clinic_id, data.patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        family_member = FamilyMember(clinic_id=clinic_id, **data.model_dump())
        return await self.repo.create(family_member)

    async def update(self, clinic_id: int | None, family_member_id: int, data: FamilyMemberUpdate) -> FamilyMember:
        family_member = await self.get(clinic_id, family_member_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(family_member, field, value)
        return await self.repo.update(family_member)

    async def soft_delete(self, clinic_id: int | None, family_member_id: int) -> None:
        family_member = await self.get(clinic_id, family_member_id)
        family_member.is_active = False
        await self.repo.update(family_member)
