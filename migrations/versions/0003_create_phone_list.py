"""create phone_list table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-07

"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS phone_list (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            phone      VARCHAR NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_phone_list_user_id ON phone_list (user_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS phone_list"))
