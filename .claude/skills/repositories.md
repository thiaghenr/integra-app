
# Skill: Repositories

Follow these patterns when creating or modifying repositories.

## Base pattern

```python
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.backend.models.patient import Patient
from app.backend.repositories.base import BaseRepository

class PatientRepository(BaseRepository[Patient]):

    async def get_all(self, clinic_id: int, active_only: bool = True) -> list[Patient]:
        query = select(Patient).where(Patient.clinic_id == clinic_id)
        if active_only:
            query = query.where(Patient.is_active == True)
        result = await self.session.exec(query)
        return result.all()

    async def get_by_id(self, id: int, clinic_id: int) -> Patient | None:
        query = select(Patient).where(
            Patient.id == id,
            Patient.clinic_id == clinic_id,
            Patient.is_active == True,
        )
        result = await self.session.exec(query)
        return result.first()

    async def get_by_phone(self, phone: str, clinic_id: int) -> Patient | None:
        query = select(Patient).where(
            Patient.phone == phone,
            Patient.clinic_id == clinic_id,
            Patient.is_active == True,
        )
        result = await self.session.exec(query)
        return result.first()
```

## Rules

- **Always** filter by `clinic_id` on every query — never return cross-clinic data
- **Always** filter by `is_active == True` unless explicitly fetching inactive records
- Never access the DB directly in services or routers — always go through the repository
- Use `async/await` with `AsyncSession` — never sync sessions
- Soft delete pattern:

```python
async def soft_delete(self, id: int, clinic_id: int) -> Patient | None:
    patient = await self.get_by_id(id, clinic_id)
    if not patient:
        return None
    patient.is_active = False
    patient.updated_at = datetime.utcnow()
    self.session.add(patient)
    await self.session.commit()
    await self.session.refresh(patient)
    return patient
```

- Update pattern:

```python
async def update(self, patient: Patient, data: PatientUpdate) -> Patient:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)
    patient.updated_at = datetime.utcnow()
    self.session.add(patient)
    await self.session.commit()
    await self.session.refresh(patient)
    return patient
```

- For joins needed by bot routes, do the join in a dedicated bot repository method or in `bot_service.py` — never pollute entity repositories with bot-specific logic
