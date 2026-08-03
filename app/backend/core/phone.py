import re

DEFAULT_COUNTRY_CODE = "55"
LOCAL_DIGITS_MAX = 11


def normalize_phone(phone: str) -> str:
    """Normalize to E.164-style digits (no '+'), defaulting missing country code to Brazil (55).

    This is the value stored as-is (whatever WhatsApp/the form actually sent, just with a
    country code guaranteed) — it is NOT deduped against the optional Brazilian mobile "9".
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= LOCAL_DIGITS_MAX:
        digits = DEFAULT_COUNTRY_CODE + digits
    return digits


def canonical_phone(phone: str) -> str:
    """Search/match key: same as normalize_phone, but with the Brazilian mobile 9th-digit
    dropped when present, since WhatsApp inconsistently includes it (55 DD 9XXXXXXXX
    vs 55 DD XXXXXXXX). Two numbers that only differ by that digit resolve to the same key.
    """
    digits = normalize_phone(phone)
    if digits.startswith(DEFAULT_COUNTRY_CODE) and len(digits) == 13 and digits[4] == "9":
        return digits[:4] + digits[5:]
    return digits


def phone_variants(phone: str) -> list[str]:
    """Both possible forms of a Brazilian mobile number (with/without the optional 9th digit),
    for matching against columns that store the number as-received instead of a canonical key.
    """
    digits = normalize_phone(phone)
    variants = {digits}
    if digits.startswith(DEFAULT_COUNTRY_CODE):
        if len(digits) == 13 and digits[4] == "9":
            variants.add(digits[:4] + digits[5:])
        elif len(digits) == 12:
            variants.add(digits[:4] + "9" + digits[4:])
    return list(variants)
