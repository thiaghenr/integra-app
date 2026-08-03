from datetime import datetime

from pydantic import BaseModel

from app.backend.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    patient_id: int
    professional_id: int
    scheduled_at: datetime
    duration_minutes: int = 50
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    patient_id: int | None = None
    professional_id: int | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    status: AppointmentStatus | None = None
    notes: str | None = None


class AppointmentRead(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    professional_id: int
    scheduled_at: datetime
    duration_minutes: int
    status: AppointmentStatus
    notes: str | None
    created_by: int

    model_config = {"from_attributes": True}
