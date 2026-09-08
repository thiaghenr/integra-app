"""normalize phone numbers to E.164-style digits with Brazil default country code

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-07

"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_NORMALIZE_EXPR = """
    CASE
        WHEN length(regexp_replace({column}, '\\D', '', 'g')) <= 11
            THEN '55' || regexp_replace({column}, '\\D', '', 'g')
        ELSE regexp_replace({column}, '\\D', '', 'g')
    END
"""


def upgrade() -> None:
    for table in ("professionals", "patients"):
        expr = _NORMALIZE_EXPR.format(column="phone")
        op.execute(sa.text(f"""
            UPDATE {table}
            SET phone = {expr}
            WHERE phone IS NOT NULL AND phone <> ''
        """))

    expr = _NORMALIZE_EXPR.format(column="phone")
    op.execute(sa.text(f"""
        UPDATE phone_list
        SET phone = {expr}
        WHERE phone <> ''
    """))


def downgrade() -> None:
    # Original formatting (spacing, dashes, presence of country code) isn't preserved,
    # so this normalization cannot be meaningfully reversed.
    pass
