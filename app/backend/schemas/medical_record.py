from datetime import datetime

from pydantic import BaseModel


class MedicalRecordCreate(BaseModel):
    patient_id: int
    appointment_id: int | None = None
    title: str
    content: str
    record_date: datetime | None = None


class MedicalRecordUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    record_date: datetime | None = None


class MedicalRecordRead(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    professional_id: int
    appointment_id: int | None
    title: str
    content: str
    record_date: datetime

    model_config = {"from_attributes": True}
