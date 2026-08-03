from datetime import datetime

from sqlmodel import Field, SQLModel


class Emotion(SQLModel, table=True):
    __tablename__ = "emotions"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
