import pytest

from app.backend.core.phone import canonical_phone, normalize_phone, phone_variants


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("5545991115537", "5545991115537"),
        ("45991115537", "5545991115537"),
        ("(45) 99111-5537", "5545991115537"),
        ("45-99111-5537", "5545991115537"),
        ("+55 11 91234-5678", "5511912345678"),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_canonical_phone_drops_optional_nine_digit():
    assert canonical_phone("5545991115537") == canonical_phone("554591115537") == "554591115537"


def test_canonical_phone_leaves_non_brazilian_length_untouched():
    assert canonical_phone("11912345") == normalize_phone("11912345")


def test_phone_variants_includes_both_forms_when_nine_present():
    variants = phone_variants("5545991115537")
    assert set(variants) == {"5545991115537", "554591115537"}


def test_phone_variants_includes_both_forms_when_nine_absent():
    variants = phone_variants("554591115537")
    assert set(variants) == {"554591115537", "5545991115537"}


def test_phone_variants_single_value_when_not_brazilian_mobile_shape():
    variants = phone_variants("12345")
    assert variants == ["5512345"]
