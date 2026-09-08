"""replace mood field with intensity (1-10) on check_ins

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-31

"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE check_ins ADD COLUMN intensity INTEGER"))
    op.execute(sa.text("UPDATE check_ins SET intensity = 5 WHERE intensity IS NULL"))
    op.execute(sa.text("ALTER TABLE check_ins ALTER COLUMN intensity SET NOT NULL"))
    op.execute(sa.text(
        "ALTER TABLE check_ins ADD CONSTRAINT ck_check_ins_intensity_range CHECK (intensity BETWEEN 1 AND 10)"
    ))

    op.execute(sa.text("ALTER TABLE check_ins DROP COLUMN mood"))
    op.execute(sa.text("DROP TYPE IF EXISTS mood"))


def downgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE mood AS ENUM (
                'otimo', 'bem', 'neutro', 'mal', 'pessimo'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))
    op.execute(sa.text("ALTER TABLE check_ins ADD COLUMN mood mood"))
    op.execute(sa.text("UPDATE check_ins SET mood = 'neutro' WHERE mood IS NULL"))
    op.execute(sa.text("ALTER TABLE check_ins ALTER COLUMN mood SET NOT NULL"))

    op.execute(sa.text("ALTER TABLE check_ins DROP CONSTRAINT IF EXISTS ck_check_ins_intensity_range"))
    op.execute(sa.text("ALTER TABLE check_ins DROP COLUMN intensity"))
