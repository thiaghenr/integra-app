# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Integra** is a web-based clinic management and scheduling system for multidisciplinary healthcare clinics. Multi-clinic, role-based, session-authenticated. The PRD is the authoritative spec — read `PRD.md` for full domain model, permissions, and route definitions.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLModel, asyncpg
- **Frontend:** Jinja2 templates + vanilla HTML/CSS/JS (no build step, no React)
- **Database:** PostgreSQL 16
- **Auth:** Session-based via `itsdangerous` signed cookies (HTTP-only) for frontend; JWT Bearer for `/api/v1/` routes
- **Migrations:** Alembic
- **Container:** Docker + Docker Compose

## Common Commands

```bash
# Start full stack
docker compose up --build

# Apply migrations
docker compose exec web alembic upgrade head

# Create a new migration
docker compose exec web alembic revision --autogenerate -m "description"

# Run the app locally (without Docker)
pip install -e .
uvicorn app.main:app --reload --port 8000

# Run the full test suite (unit + integration + e2e; needs a running "db" container)
docker compose exec web pytest

# Run only one layer of the pyramid
docker compose exec web pytest tests/unit
docker compose exec web pytest tests/integration
docker compose exec web pytest tests/e2e

# Run a single test
docker compose exec web pytest tests/path/to/test_file.py::test_function_name -v
```

Integration/e2e tests run against a disposable `integra_db_test` database on the same
Postgres container — created and schema-migrated fresh on every test session (dropped and
recreated), never touching the dev `integra_db`. See `tests/conftest.py`.

Copy `.env.example` to `.env` before first run.

## Architecture

### Layered Backend

```
app/backend/
  core/      — config (pydantic-settings), async DB engine, security helpers, FastAPI deps
  models/    — SQLModel table definitions (one file per domain entity)
  schemas/   — Pydantic request/response schemas (separate from SQLModel models)
  repositories/ — async DB access, one repo per entity, base repo with common CRUD
  services/  — business logic (validation, role checks, orchestration)
routers/     — FastAPI routers, thin (call services, return responses)
  api/v1/    — JSON API routes (prefixed /api/v1/, consumed by WhatsApp chatbot)
    bot/     — enriched routes exclusively for the WhatsApp chatbot (/api/v1/bot/)
templates/   — Jinja2, organized per entity
static/      — css/style.css, js/main.js
```

### Request Flow

HTTP request → middleware (session auth → `request.state.user`) → router → service → repository → DB

### Route Separation Convention

Frontend routes return `HTMLResponse`/`TemplateResponse`. JSON API routes are strictly under `/api/v1/`. Never mix them.

```python
# Frontend
@router.get("/patients", response_class=HTMLResponse)
async def patients_page(request: Request): ...

# API
@router.get("/api/v1/patients")
async def get_patients(): ...

# Bot-only (enriched)
@router.get("/api/v1/bot/appointments")
async def bot_appointments(): ...
```

### Auth & Session

- Passwords hashed with bcrypt
- **Frontend:** Session = signed cookie (`itsdangerous` `TimestampSigner`), payload is `user_id`
- **API (`/api/v1/`):** JWT Bearer token. Flow:
  1. Chatbot calls `GET /api/v1/auth/token-by-phone` with `X-API-Key` header to get a JWT
  2. JWT is used as `Authorization: Bearer ...` for all subsequent API calls in the conversation
- Middleware validates cookie on every non-public frontend route and sets `request.state.user`
- Public paths: `/`, `/login`, `/static/*`

### Bot API Key Auth

All `/api/v1/` routes consumed by the chatbot require `X-API-Key` header for the initial token exchange. Store the key in `CHATBOT_API_KEY` env var (see `app/backend/core/config.py`). Never expose this key to patients.

### Role-Based Access

Six roles: `superadmin`, `admin`, `receptionist`, `professional`, `viewer`, `paciente`. Enforce in services, not routers.

Key rules:
- `superadmin` bypasses clinic scoping entirely (`clinic_scope()` returns `None`, i.e. all clinics) and bypasses `require_roles()` checks — reserve for internal/ops use only, never assign to clinic staff
- Professionals only see/modify their own appointments and medical records
- `GET /api/v1/appointments` auto-filters by the authenticated professional's ID when role is `professional`
- `GET /api/v1/professionals/me/patients` returns only patients with appointment history for the calling professional — never the full patient list
- Full permission matrix in `PRD.md`

### Multi-Clinic Isolation

Every entity has a `clinic_id`. All queries must filter by the current user's `clinic_id` via `clinic_scope(current_user)` — never return cross-clinic data. Exception: `superadmin` (see Role-Based Access above), which is intentionally unscoped.

## Domain Models (SQLModel)

`Clinic → User, Professional, Patient, Appointment, MedicalRecord`
`Patient → CheckIn → Emotion, BodySignal (via CheckInEmotion / CheckInBodySignal join tables), FamilyMember`
`User → PhoneList` (phone-number lookup/dedup table, see phone normalization below)

- `Professional.user_id` and `Patient.user_id` are optional FKs to `users.id` (links a login account to a professional/patient record) — not the other way around
- `Appointment` status enum: `scheduled`, `confirmed`, `completed`, `cancelled`, `no_show`
- `CheckIn` records a patient's self-reported intensity/notes at a point in time; `CheckInEmotion` and `CheckInBodySignal` are many-to-many join tables linking a check-in to clinic-defined `Emotion` and `BodySignal` taxonomy entries
- Soft deletes via `is_active` boolean (never hard delete users, patients, professionals)
- `Clinic` model currently has: `name`, `slug`, `address`, `phone`, `is_active`, `created_at`. It does **not** yet have `business_hours`, `cancel_policy`, or `timezone` — the chatbot system prompt is documented (below and in the bot integration) as requiring these fields, so this is a known gap, not an intentional simplification. Confirm with the team before assuming either the code or this doc is the source of truth.

### Phone Normalization

`app/backend/core/phone.py` defines the canonical phone-matching convention used across `User`, `Patient`, `Professional`, and `PhoneList` lookups (e.g. `by-phone` routes):
- `normalize_phone()` — digits only, defaults to Brazil country code (`55`) when no country code is present
- `canonical_phone()` — normalized, with the optional Brazilian mobile 9th digit dropped, used as the dedup/search key (`PhoneList.phone_canonical`)
- `phone_variants()` — both with/without the 9th digit, for matching columns that store the number as-received
Use these helpers rather than ad hoc phone parsing anywhere a phone number is looked up or stored.

---

## API Routes (`/api/v1/`)

These routes are the integration surface with the WhatsApp chatbot. Keep them clean, versioned, and never break their contracts without updating the chatbot as well. `API_ENDPOINTS.md` at the repo root has a more detailed, chatbot-facing writeup of the same surface (auth flow, request/response shapes) — keep both in sync when routes change.

Note: `CheckIn`, `Emotion`, `BodySignal`, and `FamilyMember` (see Domain Models) currently only have frontend routes (`app/routers/check_ins.py`, `emotions.py`, `body_signals.py`, `family_members.py`) — there are no `/api/v1/` equivalents yet and the chatbot does not consume them.

### Auth
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/auth/token` | Email + password login (global, not clinic-scoped) → JWT |
| GET | `/auth/token-by-phone` | Exchange phone number + X-API-Key for JWT |

### Professionals
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/professionals` | List clinic professionals |
| GET | `/professionals/me/patients` | Patients with appointment history for the calling professional |
| GET | `/professionals/by-phone` | Find professional by phone number |

### Patients
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/patients` | List/search patients (full clinic scope — admin/receptionist only) |
| GET | `/patients/by-phone` | Find patient by phone number |
| GET | `/patients/{patient_id}` | Get single patient |

### Appointments
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/appointments` | List appointments (auto-scoped to professional if role=professional) |
| POST | `/appointments` | Create appointment |
| PATCH | `/appointments/{id}` | Partial update (status, scheduled_at, notes, etc.) |
| GET | `/appointments/availability` | Available slots for a professional on a date (08:00–18:00, 50-min slots) |

### Users
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/users` | List users (admin only) |

---

## Bot-specific API Routes (`/api/v1/bot/`)

These routes exist **exclusively for the WhatsApp chatbot**. They return enriched,
pre-joined responses optimized for single-call resolution — the chatbot never needs
a second call to resolve an ID to a name.

**Rules:**
- Never use these routes from the frontend
- All `/bot/` routes require the same JWT Bearer auth as `/api/v1/` routes
- Use existing repositories and services — only create new schemas (`Bot*Read`) with the extra joined fields
- Never modify existing endpoints or schemas to accommodate bot needs — create a new bot route instead
- When adding a new bot route, document it here and update the chatbot's `integra_client.py`

### Appointments
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/bot/appointments` | Appointments with `patient_name`, `patient_phone`, `professional_name`, `professional_specialization` already joined |
| GET | `/bot/appointments/availability` | Available slots with `professional_name` included |

### Professionals
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/bot/professionals/me/patients` | Patient list with `name`, `phone`, `last_appointment_at` already joined |

### Bot schemas (new, do not reuse existing schemas)

```python
class BotAppointmentRead(BaseModel):
    id: int
    scheduled_at: datetime
    duration_minutes: int
    status: str
    notes: str | None
    patient_name: str
    patient_phone: str | None
    professional_name: str
    professional_specialization: str | None

class BotPatientRead(BaseModel):
    id: int
    full_name: str
    phone: str | None
    last_appointment_at: datetime | None

class BotSlotRead(BaseModel):
    time: str           # "HH:MM"
    professional_name: str
    professional_id: int
```

---

## Chatbot Tool Routing Rules

When implementing or modifying API endpoints, respect these rules that the chatbot enforces:

**For PROFESSIONAL callers:**
- "my patients" / "list patients" → ALWAYS `GET /bot/professionals/me/patients`, NEVER `GET /patients`
- "my appointments" / "my schedule" → `GET /bot/appointments` (backend auto-filters by professional)
- Search a specific patient by name/phone → `GET /patients?search=` or `GET /patients/by-phone`
- "available slots" → `GET /bot/appointments/availability`

**For PATIENT callers:**
- "my appointments" → `GET /bot/appointments?patient_id={id}`
- "available slots" → `GET /bot/appointments/availability`

**General rule:** always prefer `/bot/` enriched endpoints over generic ones for chatbot flows.

---

## Frontend Conventions

- Brand blue: `#2D7DD2`, background white `#FFFFFF`, sidebar `#F4F6F8`, text `#1A1A2E`
- Font: Inter (Google Fonts) or `system-ui` fallback, body 14px
- Fixed left sidebar 240px; collapses on mobile
- Status badges are pill-shaped and color-coded (see PRD for colors per status)
- Flash messages at top of page, auto-dismiss after 4s
- Forms max 640px on desktop, stacked label-above-input layout
- JS only for lightweight interactions (modal toggles, date pickers, dynamic selects)

## Seed Data

On first startup, create:
- Default clinic: `Integra Clinic`
- Admin user: `admin@integra.com` / `admin123` with forced password change on first login
- Warn if `SECRET_KEY` is still the default value

## Key Constraints

- All Alembic migrations from day one — no `CREATE TABLE` or `ALTER TABLE` in startup code
- `pyproject.toml` with `hatchling` as build backend (see PRD for full dependency list)
- AWS S3 via `aioboto3` is included as a dependency but out of scope for v1
- The `/api/v1/` and `/api/v1/bot/` routes are actively consumed by the WhatsApp chatbot (`integra-bot`) — treat them as a public contract
- When adding or modifying any `/api/v1/` or `/api/v1/bot/` route, always check if the chatbot's `integra_client.py` needs to be updated as well
- Never hard-delete any patient, professional, or user record — use `is_active = False`
