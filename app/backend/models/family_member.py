from datetime import datetime

from sqlmodel import Field, SQLModel


class FamilyMember(SQLModel, table=True):
    __tablename__ = "family_members"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    patient_id: int = Field(foreign_key="patients.id", index=True)
    name: str = Field(max_length=255)
    relationship: str = Field(max_length=100)
    phone: str | None = None
    email: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
