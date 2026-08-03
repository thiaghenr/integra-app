from datetime import datetime

from sqlmodel import Field, SQLModel


class MedicalRecord(SQLModel, table=True):
    __tablename__ = "medical_records"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    patient_id: int = Field(foreign_key="patients.id", index=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)
    appointment_id: int | None = Field(default=None, foreign_key="appointments.id")
    title: str = Field(max_length=255)
    content: str
    record_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
