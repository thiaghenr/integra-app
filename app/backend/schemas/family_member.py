from pydantic import BaseModel, field_validator

from app.backend.core.phone import normalize_phone


class FamilyMemberCreate(BaseModel):
    patient_id: int
    name: str
    relationship: str
    phone: str | None = None
    email: str | None = None

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class FamilyMemberUpdate(BaseModel):
    name: str | None = None
    relationship: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class FamilyMemberRead(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    name: str
    relationship: str
    phone: str | None
    email: str | None
    is_active: bool

    model_config = {"from_attributes": True}
