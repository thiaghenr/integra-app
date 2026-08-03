
# PRD — Integra: Multidisciplinary Clinic Scheduling System

## Overview

**Integra** is a web-based clinic management and scheduling system designed for multidisciplinary healthcare clinics. It supports multiple clinics, professionals (doctors, physiotherapists, psychologists, etc.), patients, and administrative users — each with role-based access control. The primary focus of the initial version is appointment scheduling, patient management, and medical records.

---

## Goals

- Provide a clean, human-centered interface for clinic staff to manage appointments and patient data.
- Support multi-clinic environments with isolated data per clinic.
- Enforce role-based permissions so each user sees and does only what they are allowed to.
- Lay a solid foundation for future WhatsApp chatbot integration (appointment booking via webhook).

---

## Tech Stack

| Layer      | Technology                                                  |
| ---------- | ----------------------------------------------------------- |
| Backend    | Python 3.12+, FastAPI (latest), SQLModel, asyncpg           |
| Frontend   | Jinja2 templates, HTML5, CSS3 (custom, no heavy frameworks) |
| Database   | PostgreSQL 16                                               |
| Auth       | Session-based (HTTP-only cookie, itsdangerous)              |
| File store | AWS S3 (via aioboto3) — for future attachments             |
| Container  | Docker + Docker Compose (local dev)                         |
| Migrations | Alembic                                                     |

> **Frontend note:** Use Jinja2 + vanilla HTML/CSS. Keep it functional and clean — no React, no build step. Reserve JavaScript for lightweight interactions (modal toggles, date pickers, dynamic selects). Target a professional, calm aesthetic: white/light-gray surfaces, a single brand accent color (e.g. `#2D7DD2` — a trustworthy blue), Inter or system-ui for body text.

---

## FastAPI Convention

All frontend-serving routes must use the `@frontend` decorator notation (as supported by the latest FastAPI `@app.get`, `@app.post` etc.) returning `HTMLResponse` or `TemplateResponse`. API-only routes (JSON) are prefixed with `/api/v1/`. This separation must be maintained throughout the project.

Example:

```python
# Frontend route
@app.get("/patients", response_class=HTMLResponse)
async def patients_page(request: Request): ...

# API route
@app.get("/api/v1/patients")
async def get_patients(): ...
```

---

## Domain Model

### Clinic

A clinic is the top-level organizational unit. All entities belong to a clinic.

| Field      | Type     | Notes                    |
| ---------- | -------- | ------------------------ |
| id         | int (PK) |                          |
| name       | str      | Clinic display name      |
| slug       | str      | Unique URL-friendly name |
| address    | str?     |                          |
| phone      | str?     |                          |
| is_active  | bool     | Default true             |
| created_at | datetime |                          |

---

### User

System users — may or may not be a professional. Every user belongs to a clinic.

| Field           | Type     | Notes                                                     |
| --------------- | -------- | --------------------------------------------------------- |
| id              | int (PK) |                                                           |
| clinic_id       | int (FK) | → clinics.id                                             |
| email           | str      | Unique per clinic                                         |
| password_hash   | str      |                                                           |
| full_name       | str      |                                                           |
| role            | enum     | `admin`, `receptionist`, `professional`, `viewer` |
| professional_id | int?     | → professionals.id (if this user is a professional)      |
| is_active       | bool     | Default true                                              |
| created_at      | datetime |                                                           |

---

### Professional

Healthcare professionals who attend patients.

| Field          | Type     | Notes                                                  |
| -------------- | -------- | ------------------------------------------------------ |
| id             | int (PK) |                                                        |
| clinic_id      | int (FK) | → clinics.id                                          |
| full_name      | str      |                                                        |
| specialization | str      | e.g. Physiotherapy, Psychology, General                |
| registration   | str?     | Professional council registration (CRM, CREFITO, etc.) |
| phone          | str?     |                                                        |
| email          | str?     |                                                        |
| is_active      | bool     | Default true                                           |
| created_at     | datetime |                                                        |

---

### Patient

Patients registered in the clinic.

| Field         | Type     | Notes                |
| ------------- | -------- | -------------------- |
| id            | int (PK) |                      |
| clinic_id     | int (FK) | → clinics.id        |
| full_name     | str      |                      |
| cpf           | str?     | Unique per clinic    |
| date_of_birth | date?    |                      |
| phone         | str?     |                      |
| email         | str?     |                      |
| address       | str?     |                      |
| notes         | str?     | General observations |
| is_active     | bool     | Default true         |
| created_at    | datetime |                      |
| updated_at    | datetime |                      |

---

### Appointment

Core entity of the system.

| Field            | Type     | Notes                                                                   |
| ---------------- | -------- | ----------------------------------------------------------------------- |
| id               | int (PK) |                                                                         |
| clinic_id        | int (FK) | → clinics.id                                                           |
| patient_id       | int (FK) | → patients.id                                                          |
| professional_id  | int (FK) | → professionals.id                                                     |
| scheduled_at     | datetime | Date and time of the appointment                                        |
| duration_minutes | int      | Default 50                                                              |
| status           | enum     | `scheduled`, `confirmed`, `completed`, `cancelled`, `no_show` |
| notes            | str?     | Receptionist or professional notes                                      |
| created_by       | int (FK) | → users.id                                                             |
| created_at       | datetime |                                                                         |
| updated_at       | datetime |                                                                         |

---

### MedicalRecord

Clinical evolution notes written by professionals after appointments.

| Field           | Type      | Notes                         |
| --------------- | --------- | ----------------------------- |
| id              | int (PK)  |                               |
| clinic_id       | int (FK)  | → clinics.id                 |
| patient_id      | int (FK)  | → patients.id                |
| professional_id | int (FK)  | → professionals.id           |
| appointment_id  | int? (FK) | → appointments.id (optional) |
| title           | str       |                               |
| content         | text      | Clinical evolution / notes    |
| record_date     | datetime  |                               |
| created_at      | datetime  |                               |
| updated_at      | datetime  |                               |

---

## Role-Based Permissions

| Feature                     | admin | receptionist | professional  | viewer |
| --------------------------- | ----- | ------------ | ------------- | ------ |
| Manage users                | ✅    | ❌           | ❌            | ❌     |
| Manage professionals        | ✅    | ❌           | ❌            | ❌     |
| Manage patients             | ✅    | ✅           | ❌            | ❌     |
| View patients               | ✅    | ✅           | ✅            | ✅     |
| Create/edit appointments    | ✅    | ✅           | ❌            | ❌     |
| View appointments           | ✅    | ✅           | ✅ (own only) | ✅     |
| Create/edit medical records | ✅    | ❌           | ✅ (own only) | ❌     |
| View medical records        | ✅    | ❌           | ✅ (own only) | ❌     |
| Manage clinic settings      | ✅    | ❌           | ❌            | ❌     |

---

## Frontend Pages & Routes

### Auth

| Route       | Method | Description                             |
| ----------- | ------ | --------------------------------------- |
| `/`       | GET    | Redirect to`/login` or `/dashboard` |
| `/login`  | GET    | Login page                              |
| `/login`  | POST   | Authenticate user                       |
| `/logout` | GET    | Clear session                           |

---

### Dashboard

| Route          | Method | Description                                |
| -------------- | ------ | ------------------------------------------ |
| `/dashboard` | GET    | Summary: today's appointments, quick stats |

---

### Users

| Route                  | Method | Description        |
| ---------------------- | ------ | ------------------ |
| `/users`             | GET    | List all users     |
| `/users/new`         | GET    | Create user form   |
| `/users/new`         | POST   | Submit new user    |
| `/users/{id}/edit`   | GET    | Edit user form     |
| `/users/{id}/edit`   | POST   | Submit user update |
| `/users/{id}/delete` | POST   | Soft-delete user   |

---

### Patients

| Route                     | Method | Description           |
| ------------------------- | ------ | --------------------- |
| `/patients`             | GET    | List patients         |
| `/patients/new`         | GET    | Create patient form   |
| `/patients/new`         | POST   | Submit new patient    |
| `/patients/{id}`        | GET    | Patient detail page   |
| `/patients/{id}/edit`   | GET    | Edit patient form     |
| `/patients/{id}/edit`   | POST   | Submit patient update |
| `/patients/{id}/delete` | POST   | Soft-delete patient   |

---

### Professionals

| Route                          | Method | Description              |
| ------------------------------ | ------ | ------------------------ |
| `/professionals`             | GET    | List professionals       |
| `/professionals/new`         | GET    | Create professional form |
| `/professionals/new`         | POST   | Submit new professional  |
| `/professionals/{id}`        | GET    | Professional detail      |
| `/professionals/{id}/edit`   | GET    | Edit form                |
| `/professionals/{id}/edit`   | POST   | Submit update            |
| `/professionals/{id}/delete` | POST   | Soft-delete              |

---

### Appointments (Scheduling)

| Route                         | Method | Description          |
| ----------------------------- | ------ | -------------------- |
| `/appointments`             | GET    | Calendar/list view   |
| `/appointments/new`         | GET    | New appointment form |
| `/appointments/new`         | POST   | Submit appointment   |
| `/appointments/{id}`        | GET    | Appointment detail   |
| `/appointments/{id}/edit`   | GET    | Edit form            |
| `/appointments/{id}/edit`   | POST   | Submit update        |
| `/appointments/{id}/cancel` | POST   | Cancel appointment   |

---

### Medical Records

| Route                          | Method | Description             |
| ------------------------------ | ------ | ----------------------- |
| `/medical-records`           | GET    | List records (filtered) |
| `/medical-records/new`       | GET    | Create record form      |
| `/medical-records/new`       | POST   | Submit new record       |
| `/medical-records/{id}`      | GET    | Record detail           |
| `/medical-records/{id}/edit` | GET    | Edit form               |
| `/medical-records/{id}/edit` | POST   | Submit update           |

---

## API Routes (JSON — `/api/v1/`)

These are for future chatbot / WhatsApp integration:

| Route                                 | Method | Description                          |
| ------------------------------------- | ------ | ------------------------------------ |
| `/api/v1/patients`                  | GET    | List patients                        |
| `/api/v1/patients/{id}`             | GET    | Patient detail                       |
| `/api/v1/professionals`             | GET    | List professionals                   |
| `/api/v1/appointments`              | GET    | List appointments                    |
| `/api/v1/appointments`              | POST   | Create appointment                   |
| `/api/v1/appointments/{id}`         | PATCH  | Update appointment status            |
| `/api/v1/appointments/availability` | GET    | Available slots by professional/date |

---

## Project Structure

```
integra/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, middleware
│   ├── routes.py                # All router includes
│   ├── backend/
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   ├── database.py      # Async engine, session factory
│   │   │   ├── security.py      # Password hash, session token
│   │   │   └── deps.py          # FastAPI dependencies (get_db, current_user, etc.)
│   │   ├── models/
│   │   │   ├── clinic.py
│   │   │   ├── user.py
│   │   │   ├── professional.py
│   │   │   ├── patient.py
│   │   │   ├── appointment.py
│   │   │   └── medical_record.py
│   │   ├── repositories/
│   │   │   ├── base.py
│   │   │   ├── clinic_repository.py
│   │   │   ├── user_repository.py
│   │   │   ├── professional_repository.py
│   │   │   ├── patient_repository.py
│   │   │   ├── appointment_repository.py
│   │   │   └── medical_record_repository.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── professional_service.py
│   │   │   ├── patient_service.py
│   │   │   ├── appointment_service.py
│   │   │   └── medical_record_service.py
│   │   └── schemas/
│   │       ├── user.py
│   │       ├── professional.py
│   │       ├── patient.py
│   │       ├── appointment.py
│   │       └── medical_record.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── users.py
│   │   ├── patients.py
│   │   ├── professionals.py
│   │   ├── appointments.py
│   │   ├── medical_records.py
│   │   └── api/
│   │       └── v1/
│   │           ├── patients.py
│   │           ├── professionals.py
│   │           └── appointments.py
├── templates/
│   ├── base.html                # Sidebar layout, nav, flash messages
│   ├── login.html
│   ├── dashboard.html
│   ├── users/
│   │   ├── list.html
│   │   ├── create.html
│   │   └── edit.html
│   ├── patients/
│   │   ├── list.html
│   │   ├── detail.html
│   │   ├── create.html
│   │   └── edit.html
│   ├── professionals/
│   │   ├── list.html
│   │   ├── detail.html
│   │   ├── create.html
│   │   └── edit.html
│   ├── appointments/
│   │   ├── list.html
│   │   ├── detail.html
│   │   ├── create.html
│   │   └── edit.html
│   └── medical_records/
│       ├── list.html
│       ├── detail.html
│       ├── create.html
│       └── edit.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── migrations/                  # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── .env.example
└── .gitignore
```

---

## Docker Setup

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY static ./static
COPY templates ./templates
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
    env_file:
      - .env
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./app:/app/app
      - ./templates:/app/templates
      - ./static:/app/static
      - ./migrations:/app/migrations

volumes:
  postgres_data:
```

### `.env.example`

```env
# App
ENV=dev
APP_NAME=Integra
APP_VERSION=1.0.0
SECRET_KEY=change-this-to-a-random-secret-key
SESSION_COOKIE_NAME=integra_session
SESSION_MAX_AGE=604800

# Database
POSTGRES_DB=integra_db
POSTGRES_USER=integra
POSTGRES_PASSWORD=integra_pass
DATABASE_URL=postgresql+asyncpg://integra:integra_pass@localhost:5432/integra_db

# AWS S3 (optional for now)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
S3_REGION=us-east-1
```

---

## Dependencies (`pyproject.toml`)

```toml
[project]
name = "integra"
version = "1.0.0"
description = "Multidisciplinary clinic scheduling system"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "jinja2>=3.1.4",
    "sqlmodel>=0.0.21",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "python-multipart>=0.0.9",
    "itsdangerous>=2.2.0",
    "bcrypt>=4.1.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "email-validator>=2.1.0",
    "aioboto3>=13.0.0",
    "greenlet>=3.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Authentication & Session

- Passwords hashed with **bcrypt**.
- Sessions stored as signed cookies using **itsdangerous** `TimestampSigner`.
- Session payload: `user_id` encoded + signed. No server-side session store needed.
- Middleware intercepts every non-public route, verifies the cookie, loads user + role into `request.state`.
- Public paths: `/`, `/login`, `/static/*`.

---

## Design Guidelines (Frontend)

- **Palette:** White (`#FFFFFF`) background, light gray sidebar (`#F4F6F8`), brand accent blue (`#2D7DD2`), text dark (`#1A1A2E`), muted gray (`#6B7280`), success green (`#16A34A`), danger red (`#DC2626`).
- **Typography:** `Inter` (Google Fonts) or `system-ui` fallback. Body 14px/1.6, headings 500 weight.
- **Layout:** Fixed left sidebar (240px) with nav links for each section. Main content area with top header showing clinic name + logged-in user. Responsive: sidebar collapses on mobile.
- **Tables:** Clean, no zebra stripes, row hover highlight, action buttons (edit/delete) right-aligned.
- **Forms:** Stacked labels above inputs, full-width on mobile, max 640px on desktop. Inline validation messages below fields.
- **Status badges:** Pill-shaped, color-coded (scheduled=blue, confirmed=green, cancelled=gray, no_show=red, completed=purple).
- **Flash messages:** Top-of-page banner, auto-dismiss after 4s, success/error variants.

---

## Seed Data (on first startup)

- Create a default clinic: `Integra Clinic`.
- Create an admin user: `admin@integra.com` / `admin123` — **force password change on first login**.
- Log a warning if `SECRET_KEY` is set to the default value.

---

## Out of Scope (v1)

- WhatsApp / chatbot integration (architecture is ready, implementation is future work).
- Email notifications.
- Payment / billing.
- Multi-tenant SaaS (clinic isolation is built in, but no self-signup flow yet).
- Mobile app.
- Report generation / PDF export.

---

## Future Considerations

- The `/api/v1/` routes are designed to serve a WhatsApp chatbot via webhook. When that phase begins, add an API key auth layer for those routes and a `POST /api/v1/webhook/whatsapp` endpoint.
- Alembic migrations are set up from day one — no manual `ALTER TABLE` in startup code.
- IAM Role-based S3 access when deploying to AWS (no hardcoded credentials).
