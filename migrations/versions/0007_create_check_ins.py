"""create check_ins table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-30

"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE mood AS ENUM (
                'otimo', 'bem', 'neutro', 'mal', 'pessimo'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS check_ins (
            id             SERIAL PRIMARY KEY,
            clinic_id      INTEGER NOT NULL REFERENCES clinics(id),
            patient_id     INTEGER NOT NULL REFERENCES patients(id),
            mood           mood NOT NULL,
            notes          VARCHAR,
            checked_in_at  TIMESTAMP NOT NULL,
            created_at     TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_check_ins_clinic_id ON check_ins (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_check_ins_patient_id ON check_ins (patient_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS check_ins"))
    op.execute(sa.text("DROP TYPE IF EXISTS mood"))
