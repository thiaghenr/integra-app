from datetime import datetime

from pydantic import BaseModel


class MedicalRecordCreate(BaseModel):
    patient_id: int
    # Required for admin/superadmin (they have no "own" professional identity to
    # default to); ignored for a professional caller, who can only ever create a
    # record under their own professional_id — see MedicalRecordService.create().
    professional_id: int | None = None
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
