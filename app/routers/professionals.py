from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_current_user, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.repositories.user_repository import UserRepository
from app.backend.schemas.professional import ProfessionalCreate, ProfessionalUpdate
from app.backend.services.professional_service import ProfessionalService

router = APIRouter(prefix="/professionals")


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_professionals(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    professionals = await service.list(clinic_scope(current_user), active_only=False)
    return _t(request).TemplateResponse(
        request, "professionals/list.html", {"user": current_user, "professionals": professionals}
    )


@router.get("/new", response_class=HTMLResponse)
async def new_professional_form(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    clinics = []
    if current_user.role == UserRole.superadmin:
        clinics = await ClinicRepository(session).list_all()
    users = await UserRepository(session).list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request, "professionals/create.html", {"user": current_user, "clinics": clinics, "users": users, "error": None}
    )


@router.post("/new", response_class=HTMLResponse)
async def create_professional(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    cpf: str = Form(...),
    specialization: str = Form(...),
    registration: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    user_id: str = Form(None),
    clinic_id: int = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    target_clinic_id = clinic_id if (current_user.role == UserRole.superadmin and clinic_id) else current_user.clinic_id
    try:
        data = ProfessionalCreate(
            name=name,
            surname=surname,
            cpf=cpf,
            specialization=specialization,
            registration=registration or None,
            phone=phone or None,
            email=email or None,
            user_id=int(user_id) if user_id else None,
        )
        professional, generated_password = await service.create(target_clinic_id, data)
    except Exception as e:
        clinics = await ClinicRepository(session).list_all() if current_user.role == UserRole.superadmin else []
        users = await UserRepository(session).list_by_clinic(clinic_scope(current_user))
        return _t(request).TemplateResponse(
            request, "professionals/create.html", {"user": current_user, "clinics": clinics, "users": users, "error": str(e)}
        )
    if generated_password:
        return _t(request).TemplateResponse(
            request,
            "professionals/detail.html",
            {"user": current_user, "professional": professional, "generated_password": generated_password},
        )
    return RedirectResponse("/professionals", status_code=302)


@router.get("/{professional_id}", response_class=HTMLResponse)
async def professional_detail(
    request: Request,
    professional_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    professional = await service.get(clinic_scope(current_user), professional_id)
    return _t(request).TemplateResponse(
        request, "professionals/detail.html", {"user": current_user, "professional": professional}
    )


@router.get("/{professional_id}/edit", response_class=HTMLResponse)
async def edit_professional_form(
    request: Request,
    professional_id: int,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    professional = await service.get(clinic_scope(current_user), professional_id)
    users = await UserRepository(session).list_by_clinic(clinic_scope(current_user))
    return _t(request).TemplateResponse(
        request,
        "professionals/edit.html",
        {"user": current_user, "professional": professional, "users": users, "error": None},
    )


@router.post("/{professional_id}/edit", response_class=HTMLResponse)
async def update_professional(
    request: Request,
    professional_id: int,
    name: str = Form(...),
    surname: str = Form(...),
    cpf: str = Form(...),
    specialization: str = Form(...),
    registration: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    user_id: str = Form(None),
    is_active: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    scope = clinic_scope(current_user)
    try:
        data = ProfessionalUpdate(
            name=name,
            surname=surname,
            cpf=cpf,
            specialization=specialization,
            registration=registration or None,
            phone=phone or None,
            email=email or None,
            user_id=int(user_id) if user_id else None,
            is_active=is_active == "on",
        )
        await service.update(scope, professional_id, data)
    except Exception as e:
        professional = await service.get(scope, professional_id)
        users = await UserRepository(session).list_by_clinic(scope)
        return _t(request).TemplateResponse(
            request,
            "professionals/edit.html",
            {"user": current_user, "professional": professional, "users": users, "error": str(e)},
        )
    return RedirectResponse("/professionals", status_code=302)


@router.post("/{professional_id}/delete")
async def delete_professional(
    professional_id: int,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = ProfessionalService(session)
    await service.soft_delete(clinic_scope(current_user), professional_id)
    return RedirectResponse("/professionals", status_code=302)
