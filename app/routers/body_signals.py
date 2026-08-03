from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.schemas.body_signal import BodySignalCreate
from app.backend.services.body_signal_service import BodySignalService

router = APIRouter(prefix="/body-signals")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_body_signals(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = BodySignalService(session)
    body_signals = await service.list(current_user.clinic_id, active_only=False)
    categories = sorted({b.category for b in body_signals})
    return _t(request).TemplateResponse(
        request,
        "body_signals/list.html",
        {"user": current_user, "body_signals": body_signals, "categories": categories},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_body_signal_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = BodySignalService(session)
    body_signals = await service.list(current_user.clinic_id, active_only=False)
    categories = sorted({b.category for b in body_signals})
    return _t(request).TemplateResponse(
        request, "body_signals/create.html", {"user": current_user, "categories": categories, "error": None}
    )


@router.post("/new", response_class=HTMLResponse)
async def create_body_signal(
    request: Request,
    category: str = Form(...),
    name: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = BodySignalService(session)
    try:
        await service.create(current_user.clinic_id, BodySignalCreate(category=category, name=name))
    except Exception as e:
        body_signals = await service.list(current_user.clinic_id, active_only=False)
        categories = sorted({b.category for b in body_signals})
        return _t(request).TemplateResponse(
            request, "body_signals/create.html", {"user": current_user, "categories": categories, "error": str(e)}
        )
    return RedirectResponse("/body-signals", status_code=302)


@router.post("/{body_signal_id}/delete")
async def delete_body_signal(
    body_signal_id: int,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = BodySignalService(session)
    await service.soft_delete(current_user.clinic_id, body_signal_id)
    return RedirectResponse("/body-signals", status_code=302)
