from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.schemas.emotion import EmotionCreate
from app.backend.services.emotion_service import EmotionService

router = APIRouter(prefix="/emotions")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_emotions(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = EmotionService(session)
    emotions = await service.list(current_user.clinic_id, active_only=False)
    return _t(request).TemplateResponse(request, "emotions/list.html", {"user": current_user, "emotions": emotions})


@router.get("/new", response_class=HTMLResponse)
async def new_emotion_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
):
    return _t(request).TemplateResponse(request, "emotions/create.html", {"user": current_user, "error": None})


@router.post("/new", response_class=HTMLResponse)
async def create_emotion(
    request: Request,
    name: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = EmotionService(session)
    try:
        await service.create(current_user.clinic_id, EmotionCreate(name=name))
    except Exception as e:
        return _t(request).TemplateResponse(
            request, "emotions/create.html", {"user": current_user, "error": str(e)}
        )
    return RedirectResponse("/emotions", status_code=302)


@router.post("/{emotion_id}/delete")
async def delete_emotion(
    emotion_id: int,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = EmotionService(session)
    await service.soft_delete(current_user.clinic_id, emotion_id)
    return RedirectResponse("/emotions", status_code=302)
