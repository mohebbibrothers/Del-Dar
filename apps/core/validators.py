import re

from django.core.exceptions import ValidationError


def validate_national_code(value: str) -> None:
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
    if not re.match(r"^09\d{9}$", value):
        raise ValidationError("شماره همراه باید ۱۱ رقم و با 09 شروع شود.")


def validate_postal_code(value: str) -> None:
    if not re.match(r"^\d{10}$", value):
        raise ValidationError("کد پستی باید دقیقاً شامل ۱۰ رقم عددی باشد.")
