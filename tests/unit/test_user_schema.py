import pytest
from pydantic import ValidationError

from app.backend.schemas.user import AdminPasswordReset


def test_admin_password_reset_accepts_valid_length():
    data = AdminPasswordReset(new_password="longenough")
    assert data.new_password == "longenough"


def test_admin_password_reset_rejects_too_short():
    with pytest.raises(ValidationError):
        AdminPasswordReset(new_password="short")
