from datetime import datetime

from pydantic import BaseModel, model_validator

# Fixed set (Ekman's basic emotions) — shared by the Create validator below
# and by routers rendering the selected set as display labels.
EMOTION_LABELS = {
    "emotion_joy": "Alegria",
    "emotion_sadness": "Tristeza",
    "emotion_fear": "Medo",
    "emotion_anger": "Raiva",
    "emotion_disgust": "Nojo",
    "emotion_surprise": "Surpresa",
}
_EMOTION_FIELDS = tuple(EMOTION_LABELS)


class EmotionDiaryEntryCreate(BaseModel):
    patient_id: int | None = None

    emotion_joy: bool = False
    emotion_sadness: bool = False
    emotion_fear: bool = False
    emotion_anger: bool = False
    emotion_disgust: bool = False
    emotion_surprise: bool = False

    situation: str
    feeling: str
    perception: str
    thought: str
    behavior: str
    reaction: str
    outcome: str
    notes: str | None = None
    entry_date: datetime | None = None

    @model_validator(mode="after")
    def _at_least_one_emotion(self) -> "EmotionDiaryEntryCreate":
        if not any(getattr(self, field) for field in _EMOTION_FIELDS):
            raise ValueError("Selecione ao menos uma emoção do dia")
        return self


class EmotionDiaryEntryUpdate(BaseModel):
    emotion_joy: bool | None = None
    emotion_sadness: bool | None = None
    emotion_fear: bool | None = None
    emotion_anger: bool | None = None
    emotion_disgust: bool | None = None
    emotion_surprise: bool | None = None

    situation: str | None = None
    feeling: str | None = None
    perception: str | None = None
    thought: str | None = None
    behavior: str | None = None
    reaction: str | None = None
    outcome: str | None = None
    notes: str | None = None


class EmotionDiaryEntryRead(BaseModel):
    id: int
    clinic_id: int
    patient_id: int

    emotion_joy: bool
    emotion_sadness: bool
    emotion_fear: bool
    emotion_anger: bool
    emotion_disgust: bool
    emotion_surprise: bool

    situation: str
    feeling: str
    perception: str
    thought: str
    behavior: str
    reaction: str
    outcome: str
    notes: str | None
    entry_date: datetime

    model_config = {"from_attributes": True}
