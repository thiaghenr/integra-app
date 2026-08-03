from pydantic import BaseModel


class BodySignalCreate(BaseModel):
    category: str
    name: str
