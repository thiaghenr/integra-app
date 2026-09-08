"""add paciente role

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07

"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'paciente'")


def downgrade() -> None:
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("""
        CREATE TYPE userrole AS ENUM (
            'superadmin', 'admin', 'receptionist', 'professional', 'viewer'
        )
    """)
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer'")
    op.execute("DROP TYPE userrole_old")
