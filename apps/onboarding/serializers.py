from django.contrib.auth import get_user_model
from rest_framework import serializers

import jdatetime

from apps.core.validators import (
    validate_iranian_mobile,
    validate_national_code,
    validate_postal_code,
    normalize_digits,
)
from apps.works.validators import validate_work_image

User = get_user_model()


class NormalizedDigitField(serializers.CharField):
    """CharField that normalizes Persian/Arabic digits to English before validation."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = normalize_digits(data)
        return super().to_internal_value(data)


class JalaliDateField(serializers.DateField):
    """
    Accepts Jalali date in YYYY-MM-DD or YYYY/MM/DD format (with Persian/Arabic/English digits)
    and converts to Gregorian for storage.
    """

    def to_internal_value(self, data):
        if data is None:
            return None
        if isinstance(data, str):
            data = normalize_digits(data)
            sep = "-" if "-" in data else "/"
            parts = data.split(sep)
            if len(parts) == 3:
                try:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    if 1300 <= year <= 1500:
                        jd = jdatetime.date(year, month, day)
                        return jd.togregorian()
                except (ValueError, TypeError):
                    pass
        return super().to_internal_value(data)


class Step1PersonalInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    job = serializers.CharField(max_length=150)
    birth_date = JalaliDateField()
    national_code = NormalizedDigitField(max_length=10, validators=[validate_national_code])
    mobile = NormalizedDigitField(max_length=11, validators=[validate_iranian_mobile])

    def validate_national_code(self, value):
        if User.objects.filter(national_code=value).exists():
            raise serializers.ValidationError("کاربری با این کد ملی قبلا ثبت شده است.")
        return value

    def validate_mobile(self, value):
        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("این شماره همراه قبلاً در سیستم ثبت شده است.")
        return value


class Step2SupplementaryInfoSerializer(serializers.Serializer):
    province = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    address = serializers.CharField()
    postal_code = NormalizedDigitField(max_length=10, validators=[validate_postal_code])
    bale_id = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True
    )
    telegram_id = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True
    )


class DraftWorkUploadSerializer(serializers.Serializer):
    image = serializers.ImageField(validators=[validate_work_image])
    description = serializers.CharField()


class OTPVerifySerializer(serializers.Serializer):
    otp_code = NormalizedDigitField(max_length=10)
