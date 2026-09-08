"""backfill phone_list from professionals and patients

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-07

"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO phone_list (user_id, phone, created_at, updated_at)
        SELECT user_id, phone, now(), now()
        FROM professionals
        WHERE user_id IS NOT NULL AND phone IS NOT NULL AND phone <> ''
        UNION
        SELECT user_id, phone, now(), now()
        FROM patients
        WHERE user_id IS NOT NULL AND phone IS NOT NULL AND phone <> ''
    """))


def downgrade() -> None:
    op.execute(sa.text("""
        DELETE FROM phone_list pl
        WHERE EXISTS (
            SELECT 1 FROM professionals p WHERE p.user_id = pl.user_id AND p.phone = pl.phone
        ) OR EXISTS (
            SELECT 1 FROM patients pt WHERE pt.user_id = pl.user_id AND pt.phone = pl.phone
        )
    """))
