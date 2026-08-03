from datetime import datetime

from sqlmodel import Field, SQLModel


class BodySignal(SQLModel, table=True):
    __tablename__ = "body_signals"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    category: str = Field(max_length=100)
    name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
