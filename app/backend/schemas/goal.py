from datetime import date

from pydantic import BaseModel

from app.backend.models.goal import ProgressStatus


class GoalCreate(BaseModel):
    patient_id: int
    title: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProgressStatus | None = None


class GoalStatusUpdate(BaseModel):
    status: ProgressStatus


class GoalRead(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    professional_id: int
    title: str
    description: str | None
    start_date: date | None
    end_date: date | None
    status: ProgressStatus
    is_active: bool

    model_config = {"from_attributes": True}
