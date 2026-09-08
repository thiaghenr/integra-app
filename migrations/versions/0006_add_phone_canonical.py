"""add canonical phone match key to phone_list

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-07

"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Brazilian mobile numbers may or may not carry the extra "9" WhatsApp inconsistently
# sends (55 DD 9XXXXXXXX vs 55 DD XXXXXXXX). The canonical key always drops it, so both
# variants resolve to the same contact.
_CANONICAL_EXPR = """
    CASE
        WHEN phone LIKE '55%' AND length(phone) = 13 AND substr(phone, 5, 1) = '9'
            THEN substr(phone, 1, 4) || substr(phone, 6)
        ELSE phone
    END
"""


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE phone_list ADD COLUMN phone_canonical VARCHAR"))
    op.execute(sa.text(f"UPDATE phone_list SET phone_canonical = {_CANONICAL_EXPR}"))
    op.execute(sa.text("ALTER TABLE phone_list ALTER COLUMN phone_canonical SET NOT NULL"))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_phone_list_phone_canonical ON phone_list (phone_canonical)"
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_phone_list_phone_canonical"))
    op.execute(sa.text("ALTER TABLE phone_list DROP COLUMN phone_canonical"))
