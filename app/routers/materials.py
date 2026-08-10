from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.schemas.material import MaterialImport
from app.backend.services.material_service import MaterialService

router = APIRouter(prefix="/materials")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_materials(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MaterialService(session)
    materials = await service.list(scope, current_user)
    return _t(request).TemplateResponse(request, "materials/list.html", {"user": current_user, "materials": materials})


@router.get("/new", response_class=HTMLResponse)
async def new_material_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
):
    return _t(request).TemplateResponse(request, "materials/create.html", {"user": current_user, "error": None})


@router.post("/new", response_class=HTMLResponse)
async def create_material(
    request: Request,
    title: str = Form(...),
    level: int = Form(...),
    source_url: str = Form(...),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    service = MaterialService(session)
    try:
        data = MaterialImport(title=title, level=level, source_url=source_url)
        material = await service.import_from_google_docs(current_user.clinic_id, data, current_user)
    except (ValidationError, ValueError, RuntimeError) as e:
        return _t(request).TemplateResponse(request, "materials/create.html", {"user": current_user, "error": str(e)})
    return RedirectResponse(f"/materials/{material.id}", status_code=302)


@router.get("/{material_id}", response_class=HTMLResponse)
async def view_material(
    request: Request,
    material_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MaterialService(session)
    material = await service.get(scope, material_id, current_user)
    return _t(request).TemplateResponse(request, "materials/detail.html", {"user": current_user, "material": material})


@router.post("/{material_id}/reimport")
async def reimport_material(
    material_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MaterialService(session)
    await service.reimport(scope, material_id, current_user)
    return RedirectResponse(f"/materials/{material_id}", status_code=302)


@router.post("/{material_id}/delete")
async def delete_material(
    material_id: int,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.professional)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = MaterialService(session)
    await service.soft_delete(scope, material_id, current_user)
    return RedirectResponse("/materials", status_code=302)
