from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.schemas.user import AdminPasswordReset, UserCreate, UserUpdate
from app.backend.services.user_service import UserService

router = APIRouter(prefix="/users")

# paciente/professional accounts must be created via Patients/Professionals (which link a
# Patient/Professional record to the login) — creating them here would leave an orphan login
# with no linked profile, breaking every patient/professional-facing route.
_CREATABLE_ROLES = tuple(r for r in UserRole if r not in (UserRole.paciente, UserRole.professional))


def _t(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def list_users(
    request: Request,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    users = await service.list(clinic_scope(current_user))
    return _t(request).TemplateResponse(request, "users/list.html", {"user": current_user, "users": users})


@router.get("/new", response_class=HTMLResponse)
async def new_user_form(
    request: Request,
    selected_clinic_id: int = Query(None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    clinics = []
    if current_user.role == UserRole.superadmin:
        clinics = await ClinicRepository(session).list_all()

    return _t(request).TemplateResponse(
        request,
        "users/create.html",
        {
            "user": current_user,
            "clinics": clinics,
            "selected_clinic_id": selected_clinic_id,
            "roles": _CREATABLE_ROLES,
            "error": None,
        },
    )


@router.post("/new", response_class=HTMLResponse)
async def create_user(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    phone: str = Form(None),
    clinic_id: int = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    target_clinic_id = clinic_id if (current_user.role == UserRole.superadmin and clinic_id) else current_user.clinic_id
    service = UserService(session)
    try:
        parsed_role = UserRole(role)
        if parsed_role not in _CREATABLE_ROLES:
            raise HTTPException(
                status_code=400,
                detail="Contas de paciente/profissional devem ser criadas em Pacientes/Profissionais.",
            )
        data = UserCreate(
            email=email,
            name=name,
            surname=surname,
            password=password,
            role=parsed_role,
            phone=phone or None,
        )
        await service.create(target_clinic_id, data)
    except Exception as e:
        clinics = await ClinicRepository(session).list_all() if current_user.role == UserRole.superadmin else []
        return _t(request).TemplateResponse(
            request,
            "users/create.html",
            {
                "user": current_user,
                "clinics": clinics,
                "selected_clinic_id": clinic_id,
                "roles": _CREATABLE_ROLES,
                "error": e.detail if isinstance(e, HTTPException) else str(e),
            },
        )
    return RedirectResponse("/users", status_code=302)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = UserService(session)
    target = await service.get(scope, user_id)
    editable_roles = _CREATABLE_ROLES if target.role in _CREATABLE_ROLES else (*_CREATABLE_ROLES, target.role)
    return _t(request).TemplateResponse(
        request,
        "users/edit.html",
        {"user": current_user, "target": target, "roles": editable_roles, "error": None},
    )


@router.post("/{user_id}/edit", response_class=HTMLResponse)
async def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    surname: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    is_active: str = Form(None),
    new_password: str = Form(None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = UserService(session)
    try:
        target = await service.get(scope, user_id)
        parsed_role = UserRole(role)
        if parsed_role not in _CREATABLE_ROLES and parsed_role != target.role:
            raise HTTPException(
                status_code=400,
                detail="Contas de paciente/profissional devem ser vinculadas em Pacientes/Profissionais.",
            )
        data = UserUpdate(
            email=email,
            name=name,
            surname=surname,
            role=parsed_role,
            is_active=is_active == "on",
        )
        await service.update(scope, user_id, data)
        if new_password:
            await service.reset_password(scope, user_id, AdminPasswordReset(new_password=new_password))
    except Exception as e:
        target = await service.get(scope, user_id)
        editable_roles = _CREATABLE_ROLES if target.role in _CREATABLE_ROLES else (*_CREATABLE_ROLES, target.role)
        return _t(request).TemplateResponse(
            request,
            "users/edit.html",
            {
                "user": current_user,
                "target": target,
                "roles": editable_roles,
                "error": e.detail if isinstance(e, HTTPException) else str(e),
            },
        )
    return RedirectResponse("/users", status_code=302)


@router.post("/{user_id}/delete")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    await service.soft_delete(clinic_scope(current_user), user_id)
    return RedirectResponse("/users", status_code=302)
