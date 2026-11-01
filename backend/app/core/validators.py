import re
from typing import Optional


def clean_phone(value: Optional[str]) -> Optional[str]:
    """Turn what a person typed into a 10 digit Indian mobile number, or refuse it.

    Spaces, dashes and a leading +91 or 0 are accepted and removed. The result must be exactly 10 digits and start
    with 6, 7, 8 or 9, so "12345" or "98765" are rejected instead of being saved.
    """
    if value is None:
        return None
    digits = re.sub(r"[\s\-()]", "", value.strip())
    digits = re.sub(r"^(\+91|91|0)(?=\d{10}$)", "", digits)
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Enter a valid 10 digit mobile number, for example 9876543210.")
    return digits


MAX_MONEY = 10_000_000  # no single price, payment or invoice line is ever larger than one crore rupees

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def text_rule(label: str, min_len: int = 1, max_len: int = 255):
    """A field validator for free text: trims the ends and refuses blank, too short or too long values."""

    def check(value):
        if value is None:
            return None
        value = value.strip()
        if len(value) < min_len:
            raise ValueError(f"{label} must be at least {min_len} character{'s' if min_len != 1 else ''} (spaces do not count).")
        if len(value) > max_len:
            raise ValueError(f"{label} must be at most {max_len} characters.")
        return value

    return check


def clean_email(value: Optional[str]) -> Optional[str]:
    """Trim, lower-case and check the shape of an email address."""
    if value is None:
        return None
    value = value.strip().lower()
    if len(value) > 255 or not _EMAIL.match(value):
        raise ValueError("Enter a valid email address, for example name@example.com.")
    return value


def strong_password(value: str) -> str:
    """At least 8 characters with a letter and a number."""
    if not (8 <= len(value) <= 128) or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("The password must be 8 to 128 characters and contain at least one letter and one number.")
    return value


SERIAL_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9\-_/.]{2,99}$"
