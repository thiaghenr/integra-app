import pytest

from app.backend.core.db_logging import is_destructive_statement


@pytest.mark.parametrize(
    "statement",
    [
        "DROP TABLE users",
        "DROP DATABASE integra_db",
        "drop table users",  # case-insensitive
        "TRUNCATE TABLE appointments",
        "TRUNCATE appointments, patients",
        "ALTER TABLE patients DROP COLUMN notes",
        "DELETE FROM users",
        "DELETE FROM users;",
        "  delete from users  ",
    ],
)
def test_flags_destructive_statements(statement):
    assert is_destructive_statement(statement) is True


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM users WHERE id = %s",
        "INSERT INTO users (email) VALUES (%s)",
        "UPDATE users SET name = %s WHERE id = %s",
        "DELETE FROM users WHERE id = %s",
        "DELETE FROM users WHERE clinic_id = %s AND is_active = false",
        "ALTER TABLE patients ADD COLUMN level INTEGER",
        "CREATE TABLE materials (id SERIAL PRIMARY KEY)",
        "SELECT column_name FROM information_schema.columns",
    ],
)
def test_does_not_false_positive_on_normal_statements(statement):
    assert is_destructive_statement(statement) is False
