from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.models.material import Material
from app.backend.repositories.base import BaseRepository


class MaterialRepository(BaseRepository[Material]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Material, session)

    async def list_by_clinic(self, clinic_id: int | None, max_level: int | None = None) -> list[Material]:
        stmt = select(Material).where(Material.is_active == True)  # noqa: E712
        if clinic_id is not None:
            stmt = stmt.where(Material.clinic_id == clinic_id)
        if max_level is not None:
            stmt = stmt.where(Material.level <= max_level)
        stmt = stmt.order_by(Material.level, Material.title)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_clinic(self, clinic_id: int | None, material_id: int) -> Material | None:
        stmt = select(Material).where(Material.id == material_id)
        if clinic_id is not None:
            stmt = stmt.where(Material.clinic_id == clinic_id)
        result = await self.session.exec(stmt)
        return result.first()
