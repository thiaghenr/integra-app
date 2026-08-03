from pydantic import BaseModel, computed_field, field_validator

from app.backend.core.phone import normalize_phone


class ProfessionalCreate(BaseModel):
    name: str
    surname: str
    cpf: str
    specialization: str
    registration: str | None = None
    phone: str | None = None
    email: str | None = None
    user_id: int | None = None

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class ProfessionalUpdate(BaseModel):
    name: str | None = None
    surname: str | None = None
    cpf: str | None = None
    specialization: str | None = None
    registration: str | None = None
    phone: str | None = None
    email: str | None = None
    user_id: int | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class ProfessionalRead(BaseModel):
    id: int
    clinic_id: int
    user_id: int | None
    name: str
    surname: str
    cpf: str | None
    specialization: str
    registration: str | None
    phone: str | None
    email: str | None
    is_active: bool

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    model_config = {"from_attributes": True}
