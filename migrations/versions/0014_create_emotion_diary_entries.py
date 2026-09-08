"""create emotion_diary_entries table

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-01

"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS emotion_diary_entries (
            id                SERIAL PRIMARY KEY,
            clinic_id         INTEGER NOT NULL REFERENCES clinics(id),
            patient_id        INTEGER NOT NULL REFERENCES patients(id),
            emotion_joy       BOOLEAN NOT NULL DEFAULT FALSE,
            emotion_sadness   BOOLEAN NOT NULL DEFAULT FALSE,
            emotion_fear      BOOLEAN NOT NULL DEFAULT FALSE,
            emotion_anger     BOOLEAN NOT NULL DEFAULT FALSE,
            emotion_disgust   BOOLEAN NOT NULL DEFAULT FALSE,
            emotion_surprise  BOOLEAN NOT NULL DEFAULT FALSE,
            situation         VARCHAR NOT NULL,
            feeling           VARCHAR NOT NULL,
            perception        VARCHAR NOT NULL,
            thought           VARCHAR NOT NULL,
            behavior          VARCHAR NOT NULL,
            reaction          VARCHAR NOT NULL,
            outcome           VARCHAR NOT NULL,
            notes             VARCHAR,
            entry_date        TIMESTAMP NOT NULL,
            created_at        TIMESTAMP NOT NULL,
            updated_at        TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_emotion_diary_entries_clinic_id ON emotion_diary_entries (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_emotion_diary_entries_patient_id ON emotion_diary_entries (patient_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS emotion_diary_entries"))
