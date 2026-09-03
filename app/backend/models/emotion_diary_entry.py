from datetime import datetime

from sqlmodel import Field, SQLModel


class EmotionDiaryEntry(SQLModel, table=True):
    __tablename__ = "emotion_diary_entries"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    patient_id: int = Field(foreign_key="patients.id", index=True)

    # Emoção do dia — fixed set (Ekman's basic emotions), not a
    # clinic-configurable taxonomy like the Emotion model used by check-ins.
    emotion_joy: bool = Field(default=False)
    emotion_sadness: bool = Field(default=False)
    emotion_fear: bool = Field(default=False)
    emotion_anger: bool = Field(default=False)
    emotion_disgust: bool = Field(default=False)
    emotion_surprise: bool = Field(default=False)

    situation: str
    feeling: str
    perception: str
    thought: str
    behavior: str
    reaction: str
    outcome: str
    notes: str | None = None

    entry_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
