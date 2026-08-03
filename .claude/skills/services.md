
# Skill: Services

Follow these patterns when creating or modifying services.

## Responsibilities

Services are the only place where business logic lives:

- Role-based access checks
- Validation beyond Pydantic (e.g. "can this user cancel this appointment?")
- Orchestration across multiple repositories
- Raising HTTPException with meaningful messages

Routers are thin — they call the service and return the response. Never put business logic in routers.

## Base pattern

```python
from fastapi import HTTPException, status
from app.backend.models.user import User, UserRole
from app.backend.repositories.appointment_repository import AppointmentRepository
from app.backend.schemas.appointment import AppointmentCreate, AppointmentUpdate

class AppointmentService:

    def __init__(self, repository: AppointmentRepository):
        self.repository = repository

    async def get_all(self, clinic_id: int, current_user: User) -> list[Appointment]:
        # professionals only see their own
        if current_user.role == UserRole.professional:
            return await self.repository.get_by_professional(
                current_user.professional_id, clinic_id
            )
        return await self.repository.get_all(clinic_id)

    async def create(self, data: AppointmentCreate, clinic_id: int, current_user: User) -> Appointment:
        # only admin and receptionist can create
        if current_user.role not in [UserRole.admin, UserRole.receptionist]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to create appointments"
            )
        return await self.repository.create(data, clinic_id)

    async def cancel(self, appointment_id: int, clinic_id: int, current_user: User) -> Appointment:
        appointment = await self.repository.get_by_id(appointment_id, clinic_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # professionals can only cancel their own
        if current_user.role == UserRole.professional:
            if appointment.professional_id != current_user.professional_id:
                raise HTTPException(status_code=403, detail="Not your appointment")

        return await self.repository.update(
            appointment,
            AppointmentUpdate(status="cancelled")
        )
```

## Rules

- Always check `clinic_id` matches before any operation — never trust the request body for clinic isolation
- Always raise `HTTPException` with clear `detail` messages — never return `None` silently on not found
- Role checks go in the service, never in the router or repository
- Services receive the `current_user` object — never re-fetch the user inside a service
- Never import from `routers/` inside a service — services must be framework-agnostic
