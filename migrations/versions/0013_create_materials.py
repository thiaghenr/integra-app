"""create materials table, add level to patients

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-05

"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        ALTER TABLE patients ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS materials (
            id                  SERIAL PRIMARY KEY,
            clinic_id           INTEGER NOT NULL REFERENCES clinics(id),
            title               VARCHAR(255) NOT NULL,
            level               INTEGER NOT NULL DEFAULT 1,
            content_html        TEXT NOT NULL,
            source_url          VARCHAR NOT NULL,
            source_document_id  VARCHAR(100) NOT NULL,
            imported_by         INTEGER NOT NULL REFERENCES users(id),
            imported_at         TIMESTAMP NOT NULL,
            is_active           BOOLEAN NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMP NOT NULL,
            updated_at          TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_materials_clinic_id ON materials (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_materials_level ON materials (level)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS materials"))
    op.execute(sa.text("ALTER TABLE patients DROP COLUMN IF EXISTS level"))
