from datetime import datetime

from pydantic import BaseModel, field_validator

from app.backend.core.google_docs import extract_doc_id


class MaterialImport(BaseModel):
    title: str
    level: int
    source_url: str

    @field_validator("source_url")
    @classmethod
    def _validate_google_docs_url(cls, v: str) -> str:
        # Levanta ValueError (400) se não for um link reconhecível de Google Docs.
        extract_doc_id(v)
        return v

    @field_validator("level")
    @classmethod
    def _validate_level(cls, v: int) -> int:
        if v < 1:
            raise ValueError("level deve ser >= 1")
        return v


class MaterialRead(BaseModel):
    id: int
    clinic_id: int
    title: str
    level: int
    content_html: str
    source_url: str
    imported_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
