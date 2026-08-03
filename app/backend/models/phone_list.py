from datetime import datetime

from sqlmodel import Field, SQLModel


class PhoneList(SQLModel, table=True):
    __tablename__ = "phone_list"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    phone: str
    phone_canonical: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
