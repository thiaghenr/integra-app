"""create body_signals and check_in_body_signals tables, seed default signals

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-03

"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_DEFAULT_BODY_SIGNALS = [
    ("Fisiológicos", "Respiração acelerada"),
    ("Fisiológicos", "Respiração curta"),
    ("Fisiológicos", "Palpitação"),
    ("Fisiológicos", "Suor"),
    ("Fisiológicos", "Baixa pressão"),
    ("Fisiológicos", "Tremor"),
    ("Fisiológicos", "Falta de ar"),
    ("Fisiológicos", "Pressão/aperto no peito"),
    ("Musculares", "Tensão nos ombros"),
    ("Musculares", "Mandíbula travada"),
    ("Musculares", "Apertar os dentes"),
    ("Musculares", "Punhos fechados"),
    ("Musculares", "Rigidez corporal"),
    ("Musculares", "Pernas inquietas"),
    ("Musculares", "Fraqueza nas pernas"),
    ("Musculares", "Dores musculares"),
    ("Musculares", "Dor de cabeça"),
    ("Sensoriais", "Tontura"),
    ("Sensoriais", "Sensação de desmaio"),
    ("Sensoriais", "Formigamento"),
    ("Sensoriais", "Confusão"),
    ("Sensoriais", "Nó na garganta"),
    ("Sensoriais", "Balançar as pernas"),
    ("Sensoriais", "Roer as unhas"),
]


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS body_signals (
            id         SERIAL PRIMARY KEY,
            clinic_id  INTEGER NOT NULL REFERENCES clinics(id),
            category   VARCHAR(100) NOT NULL,
            name       VARCHAR(100) NOT NULL,
            is_active  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL
        )
    """))

    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_body_signals_clinic_id ON body_signals (clinic_id)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS check_in_body_signals (
            id              SERIAL PRIMARY KEY,
            check_in_id     INTEGER NOT NULL REFERENCES check_ins(id),
            body_signal_id  INTEGER NOT NULL REFERENCES body_signals(id)
        )
    """))

    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_check_in_body_signals_check_in_id ON check_in_body_signals (check_in_id)"
    ))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_check_in_body_signals_body_signal_id ON check_in_body_signals (body_signal_id)"
    ))

    conn = op.get_bind()
    clinic_ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM clinics")).fetchall()]
    for clinic_id in clinic_ids:
        for category, name in _DEFAULT_BODY_SIGNALS:
            conn.execute(
                sa.text(
                    "INSERT INTO body_signals (clinic_id, category, name, is_active, created_at) "
                    "VALUES (:clinic_id, :category, :name, TRUE, now())"
                ),
                {"clinic_id": clinic_id, "category": category, "name": name},
            )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS check_in_body_signals"))
    op.execute(sa.text("DROP TABLE IF EXISTS body_signals"))
