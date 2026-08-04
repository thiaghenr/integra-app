from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import get_db, require_roles, require_superadmin
from app.backend.models.clinic import Clinic
from app.backend.models.user import User, UserRole
from app.backend.repositories.clinic_repository import ClinicRepository

router = APIRouter()


def _t(request: Request):
    return request.app.state.templates


# ── Superadmin: full clinic management ────────────────────────────────────────


@router.get("/clinics", response_class=HTMLResponse)
async def list_clinics(
    request: Request,
    current_user: User = Depends(require_superadmin()),
    session: AsyncSession = Depends(get_db),
):
    repo = ClinicRepository(session)
    clinics = await repo.list_all()
    return _t(request).TemplateResponse(request, "clinics/list.html", {"user": current_user, "clinics": clinics})


@router.get("/clinics/new", response_class=HTMLResponse)
async def new_clinic_form(
    request: Request,
    current_user: User = Depends(require_superadmin()),
):
    return _t(request).TemplateResponse(request, "clinics/create.html", {"user": current_user, "error": None})


@router.post("/clinics/new", response_class=HTMLResponse)
async def create_clinic(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    address: str = Form(None),
    phone: str = Form(None),
    current_user: User = Depends(require_superadmin()),
    session: AsyncSession = Depends(get_db),
):
    repo = ClinicRepository(session)
    existing = await repo.get_by_slug(slug)
    if existing:
        return _t(request).TemplateResponse(
            request, "clinics/create.html", {"user": current_user, "error": "Slug já em uso."}
        )
    clinic = Clinic(name=name, slug=slug, address=address or None, phone=phone or None)
    await repo.create(clinic)
    return RedirectResponse("/clinics", status_code=302)


@router.get("/clinics/{clinic_id}/edit", response_class=HTMLResponse)
async def edit_clinic_form(
    request: Request,
    clinic_id: int,
    current_user: User = Depends(require_superadmin()),
    session: AsyncSession = Depends(get_db),
):
    repo = ClinicRepository(session)
    clinic = await repo.get(clinic_id)
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return _t(request).TemplateResponse(
        request, "clinics/edit.html", {"user": current_user, "clinic": clinic, "error": None}
    )


@router.post("/clinics/{clinic_id}/edit", response_class=HTMLResponse)
async def update_clinic(
    request: Request,
    clinic_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    address: str = Form(None),
    phone: str = Form(None),
    is_active: str = Form(None),
    current_user: User = Depends(require_superadmin()),
    session: AsyncSession = Depends(get_db),
):
    repo = ClinicRepository(session)
    clinic = await repo.get(clinic_id)
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    existing = await repo.get_by_slug(slug)
    if existing and existing.id != clinic_id:
        return _t(request).TemplateResponse(
            request, "clinics/edit.html", {"user": current_user, "clinic": clinic, "error": "Slug já em uso."}
        )
    clinic.name = name
    clinic.slug = slug
    clinic.address = address or None
    clinic.phone = phone or None
    clinic.is_active = is_active == "on"
    await repo.update(clinic)
    return RedirectResponse("/clinics", status_code=302)


# ── Admin: edit own clinic settings ────────────────────────────────────────


@router.get("/settings/clinic", response_class=HTMLResponse)
async def clinic_settings_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    repo = ClinicRepository(session)
    clinic = await repo.get(current_user.clinic_id)
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return _t(request).TemplateResponse(
        request, "settings/clinic.html", {"user": current_user, "clinic": clinic, "error": None, "saved": False}
    )


@router.post("/settings/clinic", response_class=HTMLResponse)
async def update_clinic_settings(
    request: Request,
    name: str = Form(...),
    address: str = Form(None),
    phone: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    repo = ClinicRepository(session)
    clinic = await repo.get(current_user.clinic_id)
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    clinic.name = name
    clinic.address = address or None
    clinic.phone = phone or None
    await repo.update(clinic)
    return _t(request).TemplateResponse(
        request, "settings/clinic.html", {"user": current_user, "clinic": clinic, "error": None, "saved": True}
    )
