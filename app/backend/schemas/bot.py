from datetime import datetime

from pydantic import BaseModel


class BotAppointmentRead(BaseModel):
    id: int
    scheduled_at: datetime
    duration_minutes: int
    status: str
    notes: str | None
    patient_name: str
    patient_phone: str | None
    professional_name: str
    professional_specialization: str | None


class BotPatientRead(BaseModel):
    id: int
    full_name: str
    phone: str | None
    last_appointment_at: datetime | None


class BotSlotRead(BaseModel):
    time: str
    professional_name: str
    professional_id: int
