import pytest
from pydantic import ValidationError

from app.backend.schemas.check_in import CheckInCreate


@pytest.mark.parametrize("value", [1, 5, 10])
def test_intensity_accepts_boundary_and_mid_values(value):
    data = CheckInCreate(intensity=value)
    assert data.intensity == value


@pytest.mark.parametrize("value", [0, -1, 11, 100])
def test_intensity_rejects_out_of_range_values(value):
    with pytest.raises(ValidationError):
        CheckInCreate(intensity=value)


def test_defaults_are_empty_lists_not_shared_mutable_state():
    a = CheckInCreate(intensity=5)
    b = CheckInCreate(intensity=5)
    a.emotion_ids.append(1)
    assert b.emotion_ids == []
