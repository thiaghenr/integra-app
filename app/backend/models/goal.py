from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class ProgressStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Goal(SQLModel, table=True):
    __tablename__ = "goals"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    patient_id: int = Field(foreign_key="patients.id", index=True)
    professional_id: int = Field(foreign_key="professionals.id", index=True)
    title: str = Field(max_length=255)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProgressStatus = Field(default=ProgressStatus.pending)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
