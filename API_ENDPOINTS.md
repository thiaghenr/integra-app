# Integra API Endpoints

JSON API for the WhatsApp chatbot integration. Base URL: `http://<host>/api/v1`.
All endpoints below are under this prefix (e.g. `/auth/token` → `/api/v1/auth/token`).

## Authentication

There are two auth mechanisms. Every endpoint below states which one it needs.

### 1. API key (`X-API-Key` header)
Used only by the two endpoints that issue a JWT in the first place (no JWT exists yet at that point).
Send header `X-API-Key: <CHATBOT_API_KEY>`.

### 2. Bearer JWT (`Authorization` header)
Used by every other endpoint. Obtain a token from one of the `/auth/*` endpoints below, then send
header `Authorization: Bearer <access_token>` on every subsequent call. Tokens expire after
`JWT_EXPIRE_MINUTES` (default 60) — re-issue a new one via `/auth/token-by-phone` when a call starts
returning `401`.

### Typical chatbot flow
1. A WhatsApp message arrives from some phone number.
2. Call `GET /auth/token-by-phone` with that phone number (`X-API-Key` auth) to get a JWT for the
   User account linked to that phone.
3. Use that JWT (`Authorization: Bearer ...`) for all subsequent calls in the conversation.

### Phone number format
Phone numbers are normalized to E.164-style digits with no `+` and Brazil (`55`) as the default
country code when none is given (e.g. `(45) 99111-5537` → `5545991115537`). You do not need to
pre-format phone numbers you send as query parameters — the API normalizes and also matches
Brazilian mobile numbers whether or not they include the optional 9th digit (WhatsApp is
inconsistent about this), so `554591115537` and `5545991115537` both resolve to the same contact.

---

## Auth

### `POST /auth/token`
Get a JWT via email + password (staff login, not phone-based).

- **Auth**: none
- **Body** (JSON):
  | field | type | required | description |
  |---|---|---|---|
  | `email` | string | yes | User's email |
  | `password` | string | yes | User's password |
- **Response** `200`: `{ "access_token": string, "token_type": "bearer" }`
- **Errors**: `401` invalid credentials

### `GET /auth/token-by-phone`
Get a JWT for the User account linked to a phone number. This is the main entry point for the
WhatsApp chatbot flow.

- **Auth**: API key (`X-API-Key`)
- **Query params**:
  | param | type | required | description |
  |---|---|---|---|
  | `phone` | string | yes | Phone number in any reasonable format (see normalization above) |
- **Response** `200`: `{ "access_token": string, "token_type": "bearer" }`
- **Errors**: `401` missing/invalid API key · `404` no user found for this phone · `403` account inactive

---

## Professionals

### `GET /professionals`
List professionals in the caller's clinic.

- **Auth**: Bearer JWT (any authenticated role)
- **Query params**: none
- **Response** `200`: array of `ProfessionalRead`

### `GET /professionals/me/patients`
List the patients the calling professional has appointment history with (not the full clinic
roster — only patients they've actually been scheduled with). Use this to answer "who are my
patients?" once the chatbot has a JWT for a professional.

- **Auth**: Bearer JWT (must be a User with a linked `Professional` profile)
- **Query params**: none
- **Response** `200`: array of `PatientRead`
- **Errors**: `404` if the authenticated user has no linked professional profile

### `GET /professionals/by-phone`
Look up a single professional by phone number.

- **Auth**: Bearer JWT (any authenticated role)
- **Query params**:
  | param | type | required | description |
  |---|---|---|---|
  | `phone` | string | yes | Professional's phone number |
- **Response** `200`: `ProfessionalRead`
- **Errors**: `404` not found

---

## Patients

### `GET /patients`
List/search patients in the caller's clinic.

- **Auth**: Bearer JWT (any authenticated role)
- **Query params**:
  | param | type | required | description |
  |---|---|---|---|
  | `search` | string | no | Filters by name, surname, or CPF (partial match) |
- **Response** `200`: array of `PatientRead`

### `GET /patients/by-phone`
Look up a single patient by phone number.

- **Auth**: Bearer JWT (any authenticated role)
- **Query params**:
  | param | type | required | description |
  |---|---|---|---|
  | `phone` | string | yes | Patient's phone number |
- **Response** `200`: `PatientRead`
- **Errors**: `404` not found

### `GET /patients/{patient_id}`
Get a single patient by ID.

- **Auth**: Bearer JWT (any authenticated role)
- **Path params**: `patient_id` (int, required)
- **Response** `200`: `PatientRead`
- **Errors**: `404` not found

---

## Appointments

### `GET /appointments`
List appointments in the caller's clinic. If the caller is a `professional`, results are
automatically scoped to that professional's own appointments regardless of the `professional_id`
param.

- **Auth**: Bearer JWT (any authenticated role)
- **Query params**:
  | param | type | required | description |
  |---|---|---|---|
  | `professional_id` | int | no | Filter by professional (ignored/overridden if caller is a professional) |
- **Response** `200`: array of `AppointmentRead`

### `POST /appointments`
Create an appointment.

- **Auth**: Bearer JWT, role `admin` or `receptionist`
- **Body** (JSON, `AppointmentCreate`):
  | field | type | required | description |
  |---|---|---|---|
  | `patient_id` | int | yes | |
  | `professional_id` | int | yes | |
  | `scheduled_at` | datetime (ISO 8601) | yes | |
  | `duration_minutes` | int | no (default 50) | |
  | `notes` | string | no | |
- **Response** `200`: `AppointmentRead`

### `PATCH /appointments/{appointment_id}`
Update an appointment (partial update — only send fields you want to change).

- **Auth**: Bearer JWT, role `admin` or `receptionist`
- **Path params**: `appointment_id` (int, required)
- **Body** (JSON, `AppointmentUpdate`, all fields optional):
  | field | type | description |
  |---|---|---|
  | `patient_id` | int | |
  | `professional_id` | int | |
  | `scheduled_at` | datetime (ISO 8601) | |
  | `duration_minutes` | int | |
  | `status` | string enum: `scheduled`, `confirmed`, `completed`, `cancelled`, `no_show` | |
  | `notes` | string | |
- **Response** `200`: `AppointmentRead`

### `GET /appointments/availability`
Get open time slots for a professional on a given date (08:00–18:00, 50-minute slots minus
already-booked ones).

- **Auth**: Bearer JWT (any authenticated role)
- **Query params**:
  | param | type | required | description |
  |---|---|---|---|
  | `professional_id` | int | yes | |
  | `date` | string (`YYYY-MM-DD`) | yes | |
- **Response** `200`: array of strings, e.g. `["08:00", "08:50", "09:40", ...]`

---

## Users

### `GET /users`
List users in the caller's clinic.

- **Auth**: Bearer JWT, role `admin`
- **Query params**: none
- **Response** `200`: array of `UserRead`

---

## Response schemas

### `ProfessionalRead`
```
id: int
clinic_id: int
user_id: int | null
name: string
surname: string
full_name: string
cpf: string | null
specialization: string
registration: string | null
phone: string | null
email: string | null
is_active: bool
```

### `PatientRead`
```
id: int
clinic_id: int
user_id: int | null
name: string
surname: string
full_name: string
cpf: string | null
date_of_birth: date | null   # YYYY-MM-DD
phone: string | null
email: string | null
address: string | null
notes: string | null
is_active: bool
```

### `AppointmentRead`
```
id: int
clinic_id: int
patient_id: int
professional_id: int
scheduled_at: datetime
duration_minutes: int
status: string enum (scheduled | confirmed | completed | cancelled | no_show)
notes: string | null
created_by: int   # user id
```

### `UserRead`
```
id: int
clinic_id: int
email: string
name: string
surname: string
full_name: string
role: string enum (superadmin | admin | receptionist | professional | viewer | paciente)
is_active: bool
force_password_change: bool
```
