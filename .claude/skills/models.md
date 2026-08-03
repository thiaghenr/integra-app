
# Skill: Models

Follow these patterns when creating or modifying SQLModel models.

## Required fields on every table

Every model must have these fields — no exceptions:

```python
id: int | None = Field(default=None, primary_key=True)
clinic_id: int = Field(foreign_key="clinics.id", index=True)
is_active: bool = Field(default=True)
created_at: datetime = Field(default_factory=datetime.utcnow)
updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## Base pattern

```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class MyEntity(SQLModel, table=True):
    __tablename__ = "my_entities"

    id: int | None = Field(default=None, primary_key=True)
    clinic_id: int = Field(foreign_key="clinics.id", index=True)
    name: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## Enums

Define enums as Python `str` enums and use them as field types:

```python
from enum import Enum

class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"

class Appointment(SQLModel, table=True):
    status: AppointmentStatus = Field(default=AppointmentStatus.scheduled)
```

## Foreign keys

Always index foreign keys:

```python
patient_id: int = Field(foreign_key="patients.id", index=True)
professional_id: int = Field(foreign_key="professionals.id", index=True)
```

Optional foreign keys:

```python
professional_id: int | None = Field(default=None, foreign_key="professionals.id", index=True)
```

## Rules

- Never use `CASCADE DELETE` — use `is_active = False` instead
- Never hard-delete — always soft delete via `is_active`
- Every model must be imported in `migrations/env.py` so Alembic detects it
- Table names are always plural snake_case (`my_entities`, not `MyEntity`)
- After creating a model, always run a migration — never modify the DB manually
