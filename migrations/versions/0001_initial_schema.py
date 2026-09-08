"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-06

"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM (
                'superadmin', 'admin', 'receptionist', 'professional', 'viewer'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE appointmentstatus AS ENUM (
                'scheduled', 'confirmed', 'completed', 'cancelled', 'no_show'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS clinics (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            slug        VARCHAR(100) NOT NULL UNIQUE,
            address     VARCHAR,
            phone       VARCHAR,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_clinics_slug ON clinics (slug)
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id                    SERIAL PRIMARY KEY,
            clinic_id             INTEGER NOT NULL REFERENCES clinics(id),
            email                 VARCHAR(255) NOT NULL,
            password_hash         VARCHAR NOT NULL,
            name                  VARCHAR(255) NOT NULL,
            surname               VARCHAR(255) NOT NULL,
            role                  userrole NOT NULL DEFAULT 'viewer',
            is_active             BOOLEAN NOT NULL DEFAULT TRUE,
            force_password_change BOOLEAN NOT NULL DEFAULT FALSE,
            created_at            TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_clinic_id ON users (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS professionals (
            id             SERIAL PRIMARY KEY,
            clinic_id      INTEGER NOT NULL REFERENCES clinics(id),
            user_id        INTEGER REFERENCES users(id),
            name           VARCHAR(255) NOT NULL,
            surname        VARCHAR(255) NOT NULL,
            cpf            VARCHAR(14),
            specialization VARCHAR(255) NOT NULL,
            registration   VARCHAR(100),
            phone          VARCHAR,
            email          VARCHAR,
            is_active      BOOLEAN NOT NULL DEFAULT TRUE,
            created_at     TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_professionals_clinic_id ON professionals (clinic_id)
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS patients (
            id            SERIAL PRIMARY KEY,
            clinic_id     INTEGER NOT NULL REFERENCES clinics(id),
            user_id       INTEGER REFERENCES users(id),
            name          VARCHAR(255) NOT NULL,
            surname       VARCHAR(255) NOT NULL,
            cpf           VARCHAR(14),
            date_of_birth DATE,
            phone         VARCHAR,
            email         VARCHAR,
            address       VARCHAR,
            notes         VARCHAR,
            is_active     BOOLEAN NOT NULL DEFAULT TRUE,
            created_at    TIMESTAMP NOT NULL,
            updated_at    TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_patients_clinic_id ON patients (clinic_id)
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS appointments (
            id               SERIAL PRIMARY KEY,
            clinic_id        INTEGER NOT NULL REFERENCES clinics(id),
            patient_id       INTEGER NOT NULL REFERENCES patients(id),
            professional_id  INTEGER NOT NULL REFERENCES professionals(id),
            scheduled_at     TIMESTAMP NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 50,
            status           appointmentstatus NOT NULL DEFAULT 'scheduled',
            notes            VARCHAR,
            created_by       INTEGER NOT NULL REFERENCES users(id),
            created_at       TIMESTAMP NOT NULL,
            updated_at       TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_appointments_clinic_id ON appointments (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_appointments_patient_id ON appointments (patient_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_appointments_professional_id ON appointments (professional_id)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS medical_records (
            id              SERIAL PRIMARY KEY,
            clinic_id       INTEGER NOT NULL REFERENCES clinics(id),
            patient_id      INTEGER NOT NULL REFERENCES patients(id),
            professional_id INTEGER NOT NULL REFERENCES professionals(id),
            appointment_id  INTEGER REFERENCES appointments(id),
            title           VARCHAR(255) NOT NULL,
            content         VARCHAR NOT NULL,
            record_date     TIMESTAMP NOT NULL,
            created_at      TIMESTAMP NOT NULL,
            updated_at      TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_medical_records_clinic_id ON medical_records (clinic_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_medical_records_patient_id ON medical_records (patient_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_medical_records_professional_id ON medical_records (professional_id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS medical_records"))
    op.execute(sa.text("DROP TABLE IF EXISTS appointments"))
    op.execute(sa.text("DROP TABLE IF EXISTS patients"))
    op.execute(sa.text("DROP TABLE IF EXISTS professionals"))
    op.execute(sa.text("DROP TABLE IF EXISTS users"))
    op.execute(sa.text("DROP TABLE IF EXISTS clinics"))
    op.execute(sa.text("DROP TYPE IF EXISTS appointmentstatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS userrole"))
