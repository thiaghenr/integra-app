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

## Testing Requirements (mandatory, not optional)

Every new feature — a new route (frontend or `/api/v1/`), service method, repository method,
or model/field — must ship with tests in the same change that adds it. Do not consider a
feature "done" without them, and do not wait to be asked.

- **Unit** (`tests/unit/`): pure logic with no DB — schema validation, helpers like
  `app/backend/core/phone.py`, security helpers.
- **Integration** (`tests/integration/`): service-layer behavior against the real disposable
  test DB (`integra_db_test`, see `tests/conftest.py` / `tests/integration/conftest.py`).
  Default choice for new service methods and repository logic.
- **E2E** (`tests/e2e/`): full HTTP flow through the app — required for new frontend routes
  and for any new `/api/v1/` or `/api/v1/bot/` route, since the chatbot depends on the exact
  response shape and a service-level test alone won't catch a broken route/schema wiring.

Rules:

1. New `/api/v1/*` or `/api/v1/bot/*` route → at least one test hitting the route directly
   (integration or e2e), not just the underlying service.
2. New role/permission check → a test proving the check actually blocks the wrong role, not
   just that the right role succeeds.
3. Bug fix → add a regression test that reproduces the bug first, then fix it.
4. Before reporting a feature complete, run the relevant layer(s) locally:
   `docker compose exec web pytest tests/unit tests/integration tests/e2e` (or the specific
   file/test), and mention in the summary which tests were added.
5. If a change to `/api/v1/` or `/api/v1/bot/` also requires updating `integra-bot`'s
   `integra_client.py` (per the API Routes section below), note that as a follow-up even
   though it lives in a separate repo.

### Pre-commit setup

Hooks (ruff, mypy, and standard hygiene checks — see `.pre-commit-config.yaml`) are wired
through a project-tracked `.githooks/` directory instead of the default `.git/hooks/`, so the
hook cache and `pre-commit.log` live inside the repo at `.cache/pre-commit/` (gitignored)
instead of `~/.cache/pre-commit` on each developer's machine.

The ruff and mypy hooks specifically run out of the local `./venv` (`language: system`,
`entry: venv/bin/ruff`/`venv/bin/mypy`) rather than pre-commit's own isolated per-hook
environments — this keeps their versions pinned to `requirements-dev.txt` instead of
whatever `rev:` a remote hook repo happens to use. One-time setup per clone:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
pip install pre-commit   # or: venv/bin/pip install pre-commit
git config core.hooksPath .githooks
```

`requirements.txt` is the pinned runtime dependency set (derived from `pyproject.toml`'s
`dependencies`); `requirements-dev.txt` adds test/lint tooling on top (`-r requirements.txt`
plus the `test`/`lint` extras). Regenerate either after changing `pyproject.toml` — see the
comment at the top of each file for the exact command.

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

## Observability

Added after the Aug 8 2026 incident where the dev Postgres volume was wiped with no
record of what happened — `docker volume inspect` showed a fresh `initdb` at a specific
timestamp, but nothing in the app could say whether a migration, a manual command, or
something else caused it. This is meant to make that diagnosable next time.

### Log files

Three JSON-lines log files at the repo root (`api.log`, `database.log`, `system.log`),
one per named stdlib logger (`app.api`, `app.database`, `app.system` — see
`app/backend/core/logging_config.py`). Each logger writes to its own
`RotatingFileHandler` **and** a `StreamHandler` to stdout. The files are local/dev
convenience only — production runs on ECS Fargate with ephemeral container storage, so
stdout (captured by CloudWatch via the `awslogs` log driver, see
`infra/cdk/integra_stack.py`) is what actually persists in prod. Every line is a single
JSON object: `timestamp`, `level`, `logger`, `message`, `trace_id`, `request_id`,
`span_id`, plus whatever extra fields the call site passed.

- **`api.log`** — one line per HTTP request/response (method, path, status_code,
  duration_ms, client_ip, user_id/user_role if authenticated, request/response body
  size). WARNING for 4xx, ERROR for 5xx, INFO otherwise. Written by
  `observability_middleware` in `app/main.py`.
- **`database.log`** — one line per SQL query (statement — parameterized, never
  interpolated values — duration_ms, rowcount), via SQLAlchemy `before_cursor_execute`/
  `after_cursor_execute` events registered at the `Engine` class level in
  `app/backend/core/db_logging.py` (covers every engine in the process, including test
  engines). Any `DROP`, `TRUNCATE`, `DELETE` with no `WHERE`, or `ALTER TABLE ... DROP
  COLUMN` is logged at WARNING regardless of `LOG_LEVEL` (see
  `is_destructive_statement()`), and increments the `db_destructive_statements_total`
  metric. Every `alembic upgrade`/`downgrade` run also logs here (`migrations/env.py`):
  revision before/after, direction, timestamp, and the OS user who ran it — this is the
  piece that would have told us whether a migration caused Aug 8's wipe, as opposed to a
  manual command.
- **`system.log`** — app startup/shutdown (startup includes the loaded config with
  secrets masked — see `mask_settings()` in `config.py`), and every unhandled exception
  (full traceback + trace_id) before the generic 500 is returned.

**Known limitation, directly relevant to the Aug 8 incident:** all of the above only
covers queries and commands that go through this app's own SQLAlchemy engine or its own
`alembic` invocation. A `DROP DATABASE`, `docker compose down -v`, a manual `psql`
session, or Docker Desktop's own volume lifecycle leaves **no trace** in these logs —
they happen entirely outside the app process. If a future incident is caused by one of
those, these logs will only be able to rule *in* or rule *out* whether the app itself did
it; they can't see admin/infra-level Docker or DB operations that never call this app's
code.

### Trace correlation

`app/backend/core/tracing.py` defines request-scoped `contextvars` (`trace_id`,
`request_id`, `span_id`, plus `current_user_id`/`current_user_role`), readable from any
layer — router, service, repository, DB event hook — without threading an ID through
every function signature. `observability_middleware` (outermost middleware in
`app/main.py`, so it runs before `session_middleware`) sets them per request:

- `trace_id` — reused from an inbound `X-Trace-Id` header if present (for future
  cross-service correlation with the WhatsApp bot), otherwise a fresh UUID4. Echoed back
  in the response as `X-Trace-Id`.
- `request_id` — always freshly generated per request, even when `trace_id` was
  inherited from upstream.
- `span_id` — regenerated per DB query (see `db_logging.py`'s cursor-execute hooks), so
  nested operations within one request are distinguishable.

Every log line in all three files, for the duration of a request, carries the same
`trace_id` — a single request can be reconstructed by grepping one ID across
`api.log`/`database.log`/`system.log`. **Implementation note if you touch the
middleware:** the contextvars are deliberately *not* reset in a `finally` block around
`call_next()` — an unhandled exception propagates past `observability_middleware` to
Starlette's outer `ServerErrorMiddleware` (which is what actually invokes the
`@app.exception_handler(Exception)` handler), and that handler needs `trace_id` still
set when it runs. Skipping the reset on the error path is safe because each request runs
in its own `asyncio.Task`, so nothing leaks across requests.

### Metrics

`GET /metrics` (`app/routers/metrics.py`) exposes Prometheus-formatted output via
`prometheus_client`: `http_requests_total`/`http_request_duration_seconds` (by
method/path/status), `db_queries_total`/`db_query_duration_seconds`, and
`db_destructive_statements_total` — the metric that would have caught Aug 8 early via an
alert, once alerting is wired up (not done yet; that's infra work, out of scope here).

**Decision, not a default:** the route is only mounted when `ENV != "prod"`, with no
auth — mirrors dev/test only for now. It is deliberately **not** wired behind
`require_roles()`/JWT auth, and it is **not yet reachable in prod at all**. Revisit
before this goes to production — either put it behind the existing role-based auth, or
decide on a network-level restriction (e.g. no public route to it from outside the VPC)
and implement that as infra work.

### Config

New env vars in `app/backend/core/config.py`: `LOG_LEVEL` (default `INFO`), `LOG_DIR`
(default `.`, overridden by tests to a temp dir), `LOG_MAX_BYTES` (default 10MB),
`LOG_BACKUP_COUNT` (default 5).

## Domain Models (SQLModel)

`Clinic → User, Professional, Patient, Appointment, MedicalRecord`
`Patient → CheckIn → Emotion, BodySignal (via CheckInEmotion / CheckInBodySignal join tables), FamilyMember`
`Patient → EmotionDiaryEntry`
`User → PhoneList` (phone-number lookup/dedup table, see phone normalization below)

- `Professional.user_id` and `Patient.user_id` are optional FKs to `users.id` (links a login account to a professional/patient record) — not the other way around
- `Appointment` status enum: `scheduled`, `confirmed`, `completed`, `cancelled`, `no_show`
- `CheckIn` records a patient's self-reported intensity/notes at a point in time; `CheckInEmotion` and `CheckInBodySignal` are many-to-many join tables linking a check-in to clinic-defined `Emotion` and `BodySignal` taxonomy entries
- `EmotionDiaryEntry` ("Diário das Emoções") is a separate, structured self-report journal entry (ABC-model style: situação/emoção/percepção/pensamento/comportamento/reação/resultado, plus free notes). Its "emoção do dia" checkboxes are a **fixed** set (Ekman's six basic emotions — `emotion_joy/sadness/fear/anger/disgust/surprise` boolean columns), unlike `CheckIn`'s clinic-configurable `Emotion` taxonomy — it is intentionally not built on top of `CheckIn`/`Emotion`. Same role/access pattern as `CheckIn` (`EmotionDiaryEntryService` mirrors `CheckInService`): only `paciente` creates their own (or `superadmin` on a patient's behalf), `professional` sees only patients they have appointment history with, `admin`/`superadmin` see all in clinic scope. Frontend-only like `CheckIn` — no `/api/v1/` route (see note below).
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

Note: `CheckIn`, `Emotion`, `BodySignal`, `FamilyMember`, and `EmotionDiaryEntry` (see Domain Models) currently only have frontend routes (`app/routers/check_ins.py`, `emotions.py`, `body_signals.py`, `family_members.py`, `emotion_diary.py`) — there are no `/api/v1/` equivalents yet and the chatbot does not consume them.

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

## Infrastructure (AWS)

IaC lives in `infra/`. **AWS CDK (Python, `infra/cdk/`) is the tool actually used going
forward** — `infra/cloudformation/template.yaml` is kept only as a reference/comparison of
the same architecture and should not drift too far out of sync, but new infra work happens
in the CDK stack (`infra/cdk/integra_stack.py`).

Architecture decisions (all deliberate, not defaults — see chat history for the cost
reasoning): single shared VPC for all environments, ECS Fargate tasks in a **public** subnet
with their own public IP (no ALB, no NAT gateway — both were the two biggest line items in
the cost estimate), TLS terminated by a `caddy` sidecar container in the same task
(automatic Let's Encrypt via `caddy reverse-proxy`), RDS PostgreSQL single-AZ in an isolated
private subnet with no internet route. DB credentials come from the RDS-managed Secrets
Manager secret (username/password only) — `entrypoint.sh` assembles `DATABASE_URL` from
`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` env
vars at container startup (falls back to a pre-set `DATABASE_URL` for local dev via `.env`),
since that combined URL doesn't exist anywhere as one secret.

Only **dev** is active right now. Prod resources exist in both `template.yaml` and
`integra_stack.py` but are commented out (search "Prod" / "prod" — every prod-related
resource, secret, and IAM policy reference is disabled together, on purpose, so re-enabling
it later means uncommenting rather than re-deriving). Do not silently reactivate prod
resources in either file without being asked.

Since the task's public IP changes on every deploy, Route 53 A records are **not** part of
either template — `deploy.yml` looks up the new task's IP via the ECS/EC2 API after deploy
and UPSERTs the Route 53 record as its last step (see below).

`infra/cdk/tests/unit/test_integra_stack.py` uses `aws_cdk.assertions.Template` to lock in
the cost/security decisions above — no NAT gateway, no ALB, only one environment's worth of
ECS service/task/RDS instance active, RDS not publicly accessible, DB password never in a
plain `Environment` var, GitHub deploy role has no long-lived IAM user/access key and is
scoped to this repo + the `main` branch only. Extend this test file (don't just eyeball
`cdk synth` output) any time the stack changes, per the project's usual testing rule.

```bash
cd infra/cdk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v      # asserts the architecture decisions above
cdk synth              # renders the actual CloudFormation
```

### CI/CD (`.github/workflows/deploy.yml`)

Push to `main` auto-deploys **dev**. `workflow_dispatch` still works for a manual run against
another environment (only meaningful once that environment exists for real in `integra_stack.py`
— today that's just dev). Flow: build image → push to ECR (not `ghcr.io` — ECS needs to pull
from the same account without cross-registry credentials) → `ecs update-service
--force-new-deployment` → wait for the service to stabilize → look up the new task's ENI public
IP → UPSERT the Route 53 A record.

There is deliberately **no separate "migrate" job**. The RDS instance sits in an isolated
private subnet with no internet route, so a GitHub-hosted runner can never reach it directly —
migrations run inside the container itself (`entrypoint.sh`, already inside the VPC) before
`uvicorn` starts, as part of the same deploy.

Auth is OIDC (`infra/cdk/integra_stack.py`'s `GithubDeployRole`) — no AWS access keys stored as
GitHub secrets. Before the first real deploy:

1. Edit `GITHUB_REPO` and `HOSTED_ZONE_ID` at the top of `integra_stack.py` (currently
   placeholders), then `cdk deploy`.
2. Under GitHub Settings → Environments → `dev`, set these repo/environment **Variables**
   (not secrets — none of this is sensitive): `AWS_DEPLOY_ROLE_ARN` (the `GithubDeployRoleArn`
   stack output), `APP_DOMAIN` (e.g. `dev.integra.example.com`), `HOSTED_ZONE_ID`, and
   optionally `AWS_REGION` (defaults to `us-east-1`).

The task IP lookup only grabs one task's IP — fine for dev (1 task). If prod (2 tasks) is
reactivated, that step needs to become a Route 53 multivalue-answer setup instead of a single
UPSERT — flagged with a `NOTE` comment at that step in `deploy.yml`.

## Key Constraints

- All Alembic migrations from day one — no `CREATE TABLE` or `ALTER TABLE` in startup code
- `pyproject.toml` with `hatchling` as build backend (see PRD for full dependency list)
- AWS S3 via `aioboto3` is included as a dependency but out of scope for v1
- The `/api/v1/` and `/api/v1/bot/` routes are actively consumed by the WhatsApp chatbot (`integra-bot`) — treat them as a public contract
- When adding or modifying any `/api/v1/` or `/api/v1/bot/` route, always check if the chatbot's `integra_client.py` needs to be updated as well
- Never hard-delete any patient, professional, or user record — use `is_active = False`
