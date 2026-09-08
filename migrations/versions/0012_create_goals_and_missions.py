"""create goals and missions tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-04

"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE progressstatus AS ENUM (
                'pending', 'in_progress', 'completed', 'cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS goals (
            id              SERIAL PRIMARY KEY,
            clinic_id       INTEGER NOT NULL REFERENCES clinics(id),
            patient_id      INTEGER NOT NULL REFERENCES patients(id),
            professional_id INTEGER NOT NULL REFERENCES professionals(id),
            title           VARCHAR(255) NOT NULL,
            description     VARCHAR,
            start_date      DATE,
            end_date        DATE,
            status          progressstatus NOT NULL DEFAULT 'pending',
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMP NOT NULL,
            updated_at      TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_goals_clinic_id ON goals (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_goals_patient_id ON goals (patient_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_goals_professional_id ON goals (professional_id)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS missions (
            id              SERIAL PRIMARY KEY,
            clinic_id       INTEGER NOT NULL REFERENCES clinics(id),
            patient_id      INTEGER NOT NULL REFERENCES patients(id),
            professional_id INTEGER NOT NULL REFERENCES professionals(id),
            title           VARCHAR(255) NOT NULL,
            description     VARCHAR,
            start_date      DATE,
            end_date        DATE,
            status          progressstatus NOT NULL DEFAULT 'pending',
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMP NOT NULL,
            updated_at      TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_missions_clinic_id ON missions (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_missions_patient_id ON missions (patient_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_missions_professional_id ON missions (professional_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS missions"))
    op.execute(sa.text("DROP TABLE IF EXISTS goals"))
    op.execute(sa.text("DROP TYPE IF EXISTS progressstatus"))
