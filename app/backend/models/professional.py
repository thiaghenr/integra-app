from datetime import datetime

from sqlmodel import Field, SQLModel


class Professional(SQLModel, table=True):
    __tablename__ = "professionals"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    user_id: int | None = Field(default=None, foreign_key="users.id")
    name: str = Field(max_length=255)
    surname: str = Field(max_length=255)
    cpf: str | None = Field(default=None, max_length=14)
    specialization: str = Field(max_length=255)
    registration: str | None = Field(default=None, max_length=100)
    phone: str | None = None
    email: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"
