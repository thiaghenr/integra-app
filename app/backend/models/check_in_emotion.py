from sqlmodel import Field, SQLModel


class CheckInEmotion(SQLModel, table=True):
    __tablename__ = "check_in_emotions"

    id: int | None = Field(default=None, primary_key=True)
    check_in_id: int = Field(foreign_key="check_ins.id", index=True)
    emotion_id: int = Field(foreign_key="emotions.id", index=True)
