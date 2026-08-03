from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.family_member import FamilyMember
from app.backend.repositories.base import BaseRepository


class FamilyMemberRepository(BaseRepository[FamilyMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FamilyMember, session)

    async def list_by_clinic(self, clinic_id: int | None, patient_id: int | None = None) -> list[FamilyMember]:
        stmt = select(FamilyMember).where(FamilyMember.is_active == True)  # noqa: E712
        if clinic_id is not None:
            stmt = stmt.where(FamilyMember.clinic_id == clinic_id)
        if patient_id is not None:
            stmt = stmt.where(FamilyMember.patient_id == patient_id)
        stmt = stmt.order_by(FamilyMember.name)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_clinic(self, clinic_id: int | None, family_member_id: int) -> FamilyMember | None:
        stmt = select(FamilyMember).where(FamilyMember.id == family_member_id)
        if clinic_id is not None:
            stmt = stmt.where(FamilyMember.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()
