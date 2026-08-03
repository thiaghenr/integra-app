from sqlmodel import Field, SQLModel


class CheckInBodySignal(SQLModel, table=True):
    __tablename__ = "check_in_body_signals"

    id: int | None = Field(default=None, primary_key=True)
    check_in_id: int = Field(foreign_key="check_ins.id", index=True)
    body_signal_id: int = Field(foreign_key="body_signals.id", index=True)
