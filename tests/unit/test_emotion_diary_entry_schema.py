import pytest
from pydantic import ValidationError

from app.backend.schemas.emotion_diary_entry import EmotionDiaryEntryCreate

_ABC_FIELDS = {
    "situation": "Discussão no trabalho",
    "feeling": "Raiva",
    "perception": "Senti que fui desrespeitado",
    "thought": "Achei que ninguém me ouve",
    "behavior": "Levantei a voz",
    "reaction": "Saí da sala",
    "outcome": "Piorou um pouco",
}


def test_rejects_entry_with_no_emotion_checked():
    with pytest.raises(ValidationError):
        EmotionDiaryEntryCreate(**_ABC_FIELDS)


def test_accepts_entry_with_exactly_one_emotion_checked():
    data = EmotionDiaryEntryCreate(emotion_anger=True, **_ABC_FIELDS)
    assert data.emotion_anger is True
    assert data.emotion_joy is False


def test_accepts_entry_with_multiple_emotions_checked():
    data = EmotionDiaryEntryCreate(emotion_anger=True, emotion_sadness=True, **_ABC_FIELDS)
    assert data.emotion_anger is True
    assert data.emotion_sadness is True
