
# Skill: Schemas

Follow these patterns when creating Pydantic/SQLModel schemas.

## Three schemas per entity — always

Every entity needs exactly three schemas:

```python
# Create — fields required for creation (no id, no timestamps)
class PatientCreate(BaseModel):
    full_name: str
    cpf: str | None = None
    phone: str | None = None
    email: str | None = None

# Update — all fields optional (partial update / PATCH)
class PatientUpdate(BaseModel):
    full_name: str | None = None
    cpf: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None

# Read — what the API returns (includes id and timestamps)
class PatientRead(BaseModel):
    id: int
    clinic_id: int
    full_name: str
    cpf: str | None
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

## Rules

- Never return the SQLModel model directly from an API route — always use a `*Read` schema
- Never include `password_hash` or any sensitive field in `*Read` schemas
- Always add `model_config = ConfigDict(from_attributes=True)` to `*Read` schemas so they work with ORM objects
- `*Create` schemas never have `id`, `clinic_id` (injected from session), or timestamps
- `*Update` schemas always have all fields optional (`field: type | None = None`)
- Place all schemas in `app/backend/schemas/{entity}.py`

## Bot schemas

Bot-specific schemas go in `app/backend/schemas/bot.py` and are prefixed with `Bot`:

```python
class BotAppointmentRead(BaseModel):
    id: int
    scheduled_at: datetime
    status: str
    patient_name: str
    patient_phone: str | None
    professional_name: str
    professional_specialization: str | None

    model_config = ConfigDict(from_attributes=True)
```

Never reuse or extend existing `*Read` schemas for bot responses — always create a new `Bot*Read`.
