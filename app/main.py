import logging
import os
import time
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.backend.core.config import mask_settings, settings
from app.backend.core.database import AsyncSessionLocal, engine
from app.backend.core.db_logging import log_query_context
from app.backend.core.deps import load_user_from_bearer, load_user_from_cookie
from app.backend.core.logging_config import api_logger, setup_logging, system_logger
from app.backend.core.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from app.backend.core.security import hash_password
from app.backend.core.tracing import (
    current_user_id_var,
    current_user_role_var,
    get_trace_id,
    new_id,
    request_id_var,
    span_id_var,
    trace_id_var,
)
from app.backend.models.clinic import Clinic
from app.backend.models.user import User, UserRole
from app.backend.repositories.clinic_repository import ClinicRepository
from app.backend.repositories.user_repository import UserRepository
from app.routes import register_routes

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/", "/login", "/logout", "/metrics"}
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
    system_logger.info("Application startup", extra={"config": mask_settings(settings)})
    await seed_database()
    yield
    system_logger.info("Application shutdown")
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
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.state.settings = settings

    if settings.ENV != "prod":
        from app.routers.metrics import router as metrics_router

        app.include_router(metrics_router)

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

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        system_logger.error(
            "Unhandled exception",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"method": request.method, "path": request.url.path},
        )
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
        # This handler is wired into Starlette's ServerErrorMiddleware, which
        # sits outside every @app.middleware("http") below — so it, not
        # observability_middleware, is what actually builds the response the
        # client receives for an unhandled exception. It has to set the
        # header itself.
        trace_id = get_trace_id()
        if trace_id:
            response.headers["X-Trace-Id"] = trace_id
        return response

    @app.middleware("http")
    async def session_middleware(request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)

        # Deliberately no try/finally around the resets below — see the
        # matching comment in observability_middleware. If call_next raises,
        # the exception needs current_user_id/role still set when it reaches
        # the outer unhandled-exception handler; not resetting on that path
        # is safe since each request runs in its own asyncio Task.
        if request.url.path.startswith("/api/v1/"):
            if request.url.path not in API_KEY_AUTH_PATHS:
                async with AsyncSessionLocal() as session:
                    user = await load_user_from_bearer(request, session)
                if user is None:
                    return JSONResponse({"detail": "Not authenticated"}, status_code=401)
                request.state.user = user
                user_token, role_token = log_query_context(user.id, user.role.value)
            else:
                request.state.user = None
                user_token = role_token = None
            response = await call_next(request)
        else:
            if request.url.path not in PUBLIC_PATHS:
                async with AsyncSessionLocal() as session:
                    user = await load_user_from_cookie(request, session)
                if user is None:
                    return RedirectResponse("/login", status_code=302)
                request.state.user = user
                user_token, role_token = log_query_context(user.id, user.role.value)
            else:
                request.state.user = None
                user_token = role_token = None
            response = await call_next(request)

        if user_token is not None:
            current_user_id_var.reset(user_token)
        if role_token is not None:
            current_user_role_var.reset(role_token)
        return response

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        """Outermost middleware (registered last => runs first): establishes
        trace_id/request_id/span_id for the whole request before anything
        else runs, so every log line emitted downstream — including from
        session_middleware's user lookup and any DB query — carries them.
        """
        if request.url.path.startswith("/static"):
            return await call_next(request)

        inbound_trace_id = request.headers.get("X-Trace-Id")
        trace_id = inbound_trace_id or new_id()
        request_id = new_id()
        span_id = new_id()

        trace_token = trace_id_var.set(trace_id)
        request_token = request_id_var.set(request_id)
        span_token = span_id_var.set(span_id)

        request_body_size = int(request.headers.get("content-length") or 0)
        route = request.scope.get("route")
        path_label = route.path if route is not None else request.url.path

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # An unhandled exception with no ExceptionMiddleware-level
            # handler propagates past this middleware entirely — call_next
            # never returns a response object here for us to log/tag, and
            # Starlette's outer ServerErrorMiddleware is what actually builds
            # one (via unhandled_exception_handler above, which attaches its
            # own X-Trace-Id header since we can't from here). Log what we
            # can at this layer, then re-raise so that handler still runs.
            # No contextvar reset on this path: it needs to stay visible to
            # that outer handler, and each request runs in its own asyncio
            # Task, so skipping the reset here can't leak into other requests.
            duration_ms = (time.perf_counter() - start) * 1000
            api_logger.error(
                f"{request.method} {request.url.path} 500",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                    "request_body_size": request_body_size,
                },
            )
            HTTP_REQUESTS_TOTAL.labels(method=request.method, path=path_label, status_code=500).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path_label).observe(duration_ms / 1000)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Trace-Id"] = trace_id

        status_code = response.status_code
        user = getattr(request.state, "user", None)
        log_extra = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
            "user_id": getattr(user, "id", None),
            "user_role": user.role.value if user is not None else None,
            "request_body_size": request_body_size,
            "response_body_size": int(response.headers.get("content-length") or 0),
        }
        message = f"{request.method} {request.url.path} {status_code}"
        if status_code >= 500:
            api_logger.error(message, extra=log_extra)
        elif status_code >= 400:
            api_logger.warning(message, extra=log_extra)
        else:
            api_logger.info(message, extra=log_extra)

        HTTP_REQUESTS_TOTAL.labels(method=request.method, path=path_label, status_code=status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path_label).observe(duration_ms / 1000)

        trace_id_var.reset(trace_token)
        request_id_var.reset(request_token)
        span_id_var.reset(span_token)
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
