from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.validators import (
    validate_iranian_mobile,
    validate_national_code,
    validate_postal_code,
)
from apps.works.models import Work
from apps.works.validators import validate_work_image

from .services import DashboardProfileService

User = get_user_model()


class DashboardProfileSerializer(serializers.ModelSerializer):
    national_code = serializers.CharField(max_length=10, validators=[validate_national_code])
    mobile = serializers.CharField(max_length=11, validators=[validate_iranian_mobile])
    postal_code = serializers.CharField(max_length=10, validators=[validate_postal_code])

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
    new_mobile = serializers.CharField(max_length=11, validators=[validate_iranian_mobile])

    def validate_new_mobile(self, value):
        user = self.context["request"].user
        if value == user.mobile:
            raise serializers.ValidationError("شماره وارد شده با شماره فعلی شما یکسان است.")
        if User.objects.exclude(pk=user.pk).filter(mobile=value).exists():
            raise serializers.ValidationError("این شماره همراه متعلق به کاربر دیگری است.")
        return value


class DashboardMobileChangeVerifySerializer(serializers.Serializer):
    new_mobile = serializers.CharField(max_length=11, validators=[validate_iranian_mobile])
    otp_code = serializers.CharField(max_length=10)


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
