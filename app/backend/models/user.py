from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    superadmin = "superadmin"
    admin = "admin"
    receptionist = "receptionist"
    professional = "professional"
    viewer = "viewer"
    paciente = "paciente"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    email: str = Field(max_length=255, index=True)
    password_hash: str
    name: str = Field(max_length=255)
    surname: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.viewer)
    is_active: bool = Field(default=True)
    force_password_change: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"
