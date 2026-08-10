from datetime import datetime

from sqlmodel import Field, SQLModel


class Material(SQLModel, table=True):
    __tablename__ = "materials"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    title: str = Field(max_length=255)
    # Paciente só vê materiais com level <= patients.level (ver MaterialService.list).
    level: int = Field(default=1, index=True)
    content_html: str
    source_url: str
    source_document_id: str = Field(max_length=100)
    imported_by: int = Field(foreign_key="users.id")
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
