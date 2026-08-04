from datetime import date

from pydantic import BaseModel

from app.backend.models.goal import ProgressStatus


class MissionCreate(BaseModel):
    patient_id: int
    title: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class MissionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProgressStatus | None = None


class MissionStatusUpdate(BaseModel):
    status: ProgressStatus


class MissionRead(BaseModel):
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
