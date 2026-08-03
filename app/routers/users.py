from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.deps import clinic_scope, get_db, require_roles
from app.backend.models.user import User, UserRole
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.schemas.user import UserCreate, UserUpdate
from app.backend.services.user_service import UserService

router = APIRouter(prefix="/users")


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
            "roles": UserRole,
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
        data = UserCreate(
            email=email,
            name=name,
            surname=surname,
            password=password,
            role=UserRole(role),
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
                "roles": UserRole,
                "error": str(e),
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
    return _t(request).TemplateResponse(
        request,
        "users/edit.html",
        {"user": current_user, "target": target, "roles": UserRole, "error": None},
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
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_db),
):
    scope = clinic_scope(current_user)
    service = UserService(session)
    try:
        data = UserUpdate(
            email=email,
            name=name,
            surname=surname,
            role=UserRole(role),
            is_active=is_active == "on",
        )
        await service.update(scope, user_id, data)
    except Exception as e:
        target = await service.get(scope, user_id)
        return _t(request).TemplateResponse(
            request,
            "users/edit.html",
            {"user": current_user, "target": target, "roles": UserRole, "error": str(e)},
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
