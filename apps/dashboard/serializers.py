from django.contrib.auth import get_user_model
from rest_framework import serializers

import jdatetime

from apps.core.validators import (
    validate_iranian_mobile,
    validate_national_code,
    validate_postal_code,
    normalize_digits,
)
from apps.works.models import Work
from apps.works.validators import validate_work_image

from .services import DashboardProfileService

User = get_user_model()


class NormalizedDigitField(serializers.CharField):
    """CharField that normalizes Persian/Arabic digits to English before validation."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = normalize_digits(data)
        return super().to_internal_value(data)


class JalaliDateField(serializers.DateField):
    """
    Handles Jalali dates for both input and output.
    - Input: accepts Jalali (YYYY-MM-DD or YYYY/MM/DD with Persian/Arabic/English digits) or Gregorian
    - Output: always returns Jalali format (YYYY/MM/DD)
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

    def to_representation(self, value):
        if value is None:
            return None
        try:
            if 1300 <= value.year <= 1500:
                return f"{value.year}/{value.month:02d}/{value.day:02d}"
            jd = jdatetime.date.fromgregorian(date=value)
            return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
        except (ValueError, TypeError, OverflowError):
            return None


class DashboardProfileSerializer(serializers.ModelSerializer):
    national_code = NormalizedDigitField(max_length=10, validators=[validate_national_code])
    mobile = NormalizedDigitField(max_length=11, validators=[validate_iranian_mobile])
    postal_code = NormalizedDigitField(max_length=10, validators=[validate_postal_code])
    birth_date = JalaliDateField()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "job",
            "birth_date",
            "national_code",
            "mobile",
            "province",
            "city",
            "address",
            "postal_code",
            "bale_id",
            "telegram_id",
            "profile_picture",
            "is_mobile_verified",
        )
        read_only_fields = ("is_mobile_verified",)

    def validate_national_code(self, value):
        user = self.context["request"].user
        if User.objects.exclude(pk=user.pk).filter(national_code=value).exists():
            raise serializers.ValidationError("این کد ملی متعلق به کاربر دیگری است.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        target_mobile = attrs.get("mobile", user.mobile)

        if target_mobile != user.mobile:
            if User.objects.exclude(pk=user.pk).filter(mobile=target_mobile).exists():
                raise serializers.ValidationError({"mobile": "این شماره همراه در سیستم موجود است."})

            is_verified = DashboardProfileService.is_mobile_change_verified(user.id, target_mobile)
            if not is_verified:
                msg = "ابتدا شماره تلفن همراه خود را تایید کنید سپس دکمه ثبت تغییرات را بزنید."
                raise serializers.ValidationError({"mobile": msg})

        return attrs


class DashboardMobileChangeRequestSerializer(serializers.Serializer):
    new_mobile = NormalizedDigitField(max_length=11, validators=[validate_iranian_mobile])

    def validate_new_mobile(self, value):
        user = self.context["request"].user
        if value == user.mobile:
            raise serializers.ValidationError("شماره وارد شده با شماره فعلی شما یکسان است.")
        if User.objects.exclude(pk=user.pk).filter(mobile=value).exists():
            raise serializers.ValidationError("این شماره همراه متعلق به کاربر دیگری است.")
        return value


class DashboardMobileChangeVerifySerializer(serializers.Serializer):
    new_mobile = NormalizedDigitField(max_length=11, validators=[validate_iranian_mobile])
    otp_code = NormalizedDigitField(max_length=10)


class DashboardWorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ("id", "image", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class DashboardWorkCreateUpdateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(validators=[validate_work_image], required=False)

    class Meta:
        model = Work
        fields = ("id", "image", "description")
