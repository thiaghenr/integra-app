import logging
import os
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.backend.core.config import settings
from app.backend.core.database import AsyncSessionLocal, engine
from app.backend.core.deps import load_user_from_bearer, load_user_from_cookie
from app.backend.core.security import hash_password
from app.backend.models.clinic import Clinic
from app.backend.models.user import User, UserRole
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.repositories.user_repository import UserRepository
from app.routes import register_routes

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/", "/login", "/logout"}
API_KEY_AUTH_PATHS = {"/api/v1/auth/token", "/api/v1/auth/token-by-phone"}


async def seed_database() -> None:
    async with AsyncSessionLocal() as session:
        clinic_repo = ClinicRepository(session)
        clinic = await clinic_repo.get_by_slug("integra-clinic")
        if not clinic:
            clinic = Clinic(name="Integra Clinic", slug="integra-clinic")
            await clinic_repo.create(clinic)
            logger.info("Created default clinic: Integra Clinic")

        user_repo = UserRepository(session)
        admin = await user_repo.get_by_email_global("admin@integra.com")
        if not admin:
            admin = User(
                clinic_id=clinic.id,
                email="admin@integra.com",
                name="Admin",
                surname="Integra",
                role=UserRole.superadmin,
                password_hash=hash_password("admin123"),
                force_password_change=True,
            )
            await user_repo.create(admin)
            logger.info("Created default superadmin user: admin@integra.com / admin123")
        elif admin.role != UserRole.superadmin:
            admin.role = UserRole.superadmin
            await user_repo.update(admin)
            logger.info("Upgraded admin@integra.com to superadmin")

    if settings.SECRET_KEY == "change-this-to-a-random-secret-key":
        warnings.warn("SECRET_KEY is set to the default value — change it before going to production!", stacklevel=1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await seed_database()
    yield
    await engine.dispose()


def _status_pt(value: str) -> str:
    return {
        "scheduled": "Agendado",
        "confirmed": "Confirmado",
        "completed": "Concluído",
        "cancelled": "Cancelado",
        "no_show": "Faltou",
        "pending": "Pendente",
        "in_progress": "Em Andamento",
    }.get(value, value.replace("_", " "))


def _role_pt(value: str) -> str:
    return {
        "superadmin": "Superadmin",
        "admin": "Administrador",
        "receptionist": "Recepcionista",
        "professional": "Profissional",
        "viewer": "Visualizador",
        "paciente": "Paciente",
    }.get(value, value)


def api() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.state.settings = settings

    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
    app.state.templates = templates

    templates.env.filters["status_pt"] = _status_pt
    templates.env.filters["role_pt"] = _role_pt

    register_routes(app)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schema.setdefault("components", {})["securitySchemes"] = {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
        for path, methods in schema.get("paths", {}).items():
            if path.startswith("/api/v1/") and path not in API_KEY_AUTH_PATHS:
                for operation in methods.values():
                    operation["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    @app.middleware("http")
    async def session_middleware(request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)

        if request.url.path.startswith("/api/v1/"):
            if request.url.path not in API_KEY_AUTH_PATHS:
                async with AsyncSessionLocal() as session:
                    user = await load_user_from_bearer(request, session)
                if user is None:
                    print("N" * 10)
                    return JSONResponse({"detail": "Not authenticated"}, status_code=401)
                request.state.user = user
            else:
                request.state.user = None
            return await call_next(request)

        if request.url.path not in PUBLIC_PATHS:
            async with AsyncSessionLocal() as session:
                user = await load_user_from_cookie(request, session)
            if user is None:
                return RedirectResponse("/login", status_code=302)
            request.state.user = user
        else:
            request.state.user = None

        response = await call_next(request)
        return response

    return app


if __name__ == "__main__":
    uvicorn.run(
        "app.main:api",
        host=os.getenv("INTEGRA_SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("INTEGRA_SERVER_PORT", "8000")),
        reload=True,
        factory=True,
    )
