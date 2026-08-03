
Create a complete new domain entity for the Integra project following the layered architecture.

This command creates the full stack for a new entity: model → schema → repository → service → router (frontend + API).

Follow ALL conventions from CLAUDE.md and PRD.md.

Steps to execute:

1. **Model** — create `app/backend/models/{entity}.py`

   - Extend SQLModel with `table=True`
   - Always include: `id`, `clinic_id` (FK → clinics.id), `is_active` (bool, default True), `created_at`, `updated_at`
   - Use soft deletes only — never hard delete
2. **Schema** — create `app/backend/schemas/{entity}.py`

   - Create: `{Entity}Create`, `{Entity}Update`, `{Entity}Read`
   - Never reuse the SQLModel model as a schema
3. **Repository** — create `app/backend/repositories/{entity}_repository.py`

   - Extend `BaseRepository`
   - All queries must filter by `clinic_id`
   - Use async/await with `AsyncSession`
4. **Service** — create `app/backend/services/{entity}_service.py`

   - Business logic, validation, role checks
   - Never access DB directly — always go through the repository
   - Enforce clinic isolation here
5. **Frontend router** — create `app/routers/{entity}s.py`

   - Routes: list, detail, create (GET+POST), edit (GET+POST), delete (POST soft)
   - Return `TemplateResponse` — never JSON
   - Protect with role checks via service
6. **API router** — create `app/routers/api/v1/{entity}s.py`

   - Routes: GET list, GET by id, POST create, PATCH update
   - Return JSON (`{Entity}Read` schema)
   - JWT Bearer auth
7. **Templates** — create `templates/{entity}s/` with:

   - `list.html`, `detail.html`, `create.html`, `edit.html`
   - Extend `base.html`
   - Follow frontend conventions from CLAUDE.md
8. **Register routers** — add both routers in `app/main.py` or `app/routes.py`
9. **Migration** — after all files are created, run:

   ```bash
   docker compose exec web alembic revision --autogenerate -m "add {entity} table"
   docker compose exec web alembic upgrade head
   ```
10. **Update CLAUDE.md** — add the new API routes to the routes table

Checklist before finishing:

- [ ] Model has clinic_id and is_active
- [ ] All repository queries filter by clinic_id
- [ ] Role checks enforced in service
- [ ] Frontend router returns TemplateResponse only
- [ ] API router returns JSON only
- [ ] Migration generated and applied
- [ ] CLAUDE.md updated

The entity to create: $ARGUMENTS
