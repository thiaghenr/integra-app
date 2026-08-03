from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    patient_id: int = Field(foreign_key="patients.id", index=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)
    scheduled_at: datetime
    duration_minutes: int = Field(default=50)
    status: AppointmentStatus = Field(default=AppointmentStatus.scheduled)
    notes: str | None = None
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
