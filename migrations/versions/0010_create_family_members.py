"""create family_members table

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-01

"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS family_members (
            id           SERIAL PRIMARY KEY,
            clinic_id    INTEGER NOT NULL REFERENCES clinics(id),
            patient_id   INTEGER NOT NULL REFERENCES patients(id),
            name         VARCHAR(255) NOT NULL,
            relationship VARCHAR(100) NOT NULL,
            phone        VARCHAR,
            email        VARCHAR,
            is_active    BOOLEAN NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_family_members_clinic_id ON family_members (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_family_members_patient_id ON family_members (patient_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS family_members"))
