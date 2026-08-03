from pydantic import BaseModel, field_validator


class CheckInCreate(BaseModel):
    patient_id: int | None = None
    intensity: int
    notes: str | None = None
    emotion_ids: list[int] = []
    body_signal_ids: list[int] = []

    @field_validator("intensity")
    @classmethod
    def _validate_intensity(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("Intensidade deve ser entre 1 e 10")
        return v
