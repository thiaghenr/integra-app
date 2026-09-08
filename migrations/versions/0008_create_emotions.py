"""create emotions and check_in_emotions tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31

"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS emotions (
            id         SERIAL PRIMARY KEY,
            clinic_id  INTEGER NOT NULL REFERENCES clinics(id),
            name       VARCHAR(100) NOT NULL,
            is_active  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_emotions_clinic_id ON emotions (clinic_id)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS check_in_emotions (
            id            SERIAL PRIMARY KEY,
            check_in_id   INTEGER NOT NULL REFERENCES check_ins(id),
            emotion_id    INTEGER NOT NULL REFERENCES emotions(id)
        )
    """))

    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_check_in_emotions_check_in_id ON check_in_emotions (check_in_id)"
    ))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_check_in_emotions_emotion_id ON check_in_emotions (emotion_id)"
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS check_in_emotions"))
    op.execute(sa.text("DROP TABLE IF EXISTS emotions"))
