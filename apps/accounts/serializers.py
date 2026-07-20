from rest_framework import serializers

from apps.core.validators import normalize_digits


class NormalizedDigitField(serializers.CharField):
    """CharField that normalizes Persian/Arabic digits to English before validation."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = normalize_digits(data)
        return super().to_internal_value(data)


class AuthLoginRequestSerializer(serializers.Serializer):
    identifier = NormalizedDigitField(max_length=20)


class AuthLoginVerifySerializer(serializers.Serializer):
    identifier = NormalizedDigitField(max_length=20)
    otp_code = NormalizedDigitField(max_length=10)
