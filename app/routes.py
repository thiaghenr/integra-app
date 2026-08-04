from fastapi import FastAPI

from app.routers import (
    auth,
    body_signals,
    check_ins,
    clinics,
    dashboard,
    emotions,
    family_members,
    goals,
    medical_records,
    missions,
    patients,
    professionals,
    users,
)
from app.routers.api.v1 import appointments as api_appointments
from app.routers.api.v1 import auth as api_auth
from app.routers.api.v1 import bot as api_bot
from app.routers.api.v1 import patients as api_patients
from app.routers.api.v1 import professionals as api_professionals
from app.routers.api.v1 import users as api_users
from app.routers.appointments import router as appointments_router


def register_routes(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(users.router)
    app.include_router(patients.router)
    app.include_router(professionals.router)
    app.include_router(appointments_router)
    app.include_router(medical_records.router)
    app.include_router(clinics.router)
    app.include_router(check_ins.router)
    app.include_router(emotions.router)
    app.include_router(body_signals.router)
    app.include_router(family_members.router)
    app.include_router(goals.router)
    app.include_router(missions.router)

    app.include_router(api_auth.router, prefix="/api/v1")
    app.include_router(api_patients.router, prefix="/api/v1")
    app.include_router(api_professionals.router, prefix="/api/v1")
    app.include_router(api_appointments.router, prefix="/api/v1")
    app.include_router(api_users.router, prefix="/api/v1")
    app.include_router(api_bot.router, prefix="/api/v1/bot")
