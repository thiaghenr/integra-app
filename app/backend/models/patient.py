from datetime import date, datetime

from sqlmodel import Field, SQLModel


class Patient(SQLModel, table=True):
    __tablename__ = "patients"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    user_id: int | None = Field(default=None, foreign_key="users.id")
    name: str = Field(max_length=255)
    surname: str = Field(max_length=255)
    cpf: str | None = Field(default=None, max_length=14)
    date_of_birth: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"
