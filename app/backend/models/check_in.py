from datetime import datetime

from sqlmodel import Field, SQLModel


class CheckIn(SQLModel, table=True):
    __tablename__ = "check_ins"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    patient_id: int = Field(foreign_key="patients.id", index=True)
    intensity: int
    notes: str | None = None
    checked_in_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
