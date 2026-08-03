from datetime import datetime

from sqlmodel import Field, SQLModel


class Clinic(SQLModel, table=True):
    __tablename__ = "clinics"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, unique=True, index=True)
    address: str | None = None
    phone: str | None = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
