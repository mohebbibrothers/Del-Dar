import re

from django.core.exceptions import ValidationError

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_ENGLISH_DIGITS = "0123456789"
_PERSIAN_TO_ENGLISH = str.maketrans(_PERSIAN_DIGITS + _ARABIC_DIGITS, _ENGLISH_DIGITS * 2)


def normalize_digits(value: str) -> str:
    """Convert Persian/Arabic digits to English digits."""
    return value.translate(_PERSIAN_TO_ENGLISH)


def validate_national_code(value: str) -> None:
    value = normalize_digits(value)
    if not re.match(r"^\d{10}$", value):
        raise ValidationError("کد ملی باید دقیقاً شامل ۱۰ رقم عددی باشد.")

    if len(set(value)) == 1:
        raise ValidationError("کد ملی وارد شده معتبر نیست.")

    check_digit = int(value[9])
    s = sum(int(value[i]) * (10 - i) for i in range(9))
    remainder = s % 11

    is_valid = (remainder < 2 and check_digit == remainder) or (
        remainder >= 2 and check_digit == 11 - remainder
    )

    if not is_valid:
        raise ValidationError("کد ملی وارد شده معتبر نیست.")


def validate_iranian_mobile(value: str) -> None:
    value = normalize_digits(value)
    if not re.match(r"^09\d{9}$", value):
        raise ValidationError("شماره همراه باید ۱۱ رقم و با 09 شروع شود.")


def validate_postal_code(value: str) -> None:
    value = normalize_digits(value)
    if not re.match(r"^\d{10}$", value):
        raise ValidationError("کد پستی باید دقیقاً شامل ۱۰ رقم عددی باشد.")
