from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.backend.core.config import settings
from app.backend.core.deps import get_current_user, get_db
from app.backend.core.security import create_session_token
from app.backend.models.user import User
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.services.auth_service import AuthService

router = APIRouter()


def _t(request: Request):
    return request.app.state.templates


@router.get("/", response_class=RedirectResponse)
async def root(request: Request):
    if getattr(request.state, "user", None):
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if getattr(request.state, "user", None):
        return RedirectResponse("/dashboard", status_code=302)
    return _t(request).TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    clinic_repo = ClinicRepository(session)
    clinic = await clinic_repo.get_by_slug("integra-clinic")
    if not clinic:
        return _t(request).TemplateResponse(request, "login.html", {"error": "Clínica não configurada."})

    try:
        auth_service = AuthService(session)
        user = await auth_service.authenticate(clinic.id, email, password)
    except Exception:
        return _t(request).TemplateResponse(request, "login.html", {"error": "E-mail ou senha inválidos."})

    token = create_session_token(user.id)
    redirect_url = "/change-password" if user.force_password_change else "/dashboard"
    response = RedirectResponse(redirect_url, status_code=302)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.SESSION_MAX_AGE,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, current_user: User = Depends(get_current_user)):
    return _t(request).TemplateResponse(request, "change_password.html", {"user": current_user, "error": None})


@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from app.backend.services.user_service import UserService

    service = UserService(session)
    try:
        await service.change_password(current_user, current_password, new_password)
    except Exception:
        return _t(request).TemplateResponse(
            request, "change_password.html", {"user": current_user, "error": "Senha atual incorreta."}
        )
    return RedirectResponse("/dashboard", status_code=302)
