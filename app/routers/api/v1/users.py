from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.user_repository import UserRepository
from app.backend.schemas.user import UserRead

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserRead])
async def api_list_users(
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    return await UserRepository(session).list_by_clinic(clinic_scope(current_user))
