from pydantic import BaseModel, EmailStr, computed_field, field_validator

from app.backend.core.phone import normalize_phone
from app.backend.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    surname: str
    role: UserRole
    password: str
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    surname: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: int
    clinic_id: int
    email: str
    name: str
    surname: str
    role: UserRole
    is_active: bool
    force_password_change: bool

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    model_config = {"from_attributes": True}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
