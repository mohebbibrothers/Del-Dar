from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.validators import (
    validate_iranian_mobile,
    validate_national_code,
    validate_postal_code,
)

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    # Personal Info (Desktop-2)
    first_name = models.CharField(max_length=100, verbose_name="نام")
    last_name = models.CharField(max_length=100, verbose_name="نام خانوادگی")
    job = models.CharField(max_length=150, verbose_name="شغل")
    birth_date = models.DateField(verbose_name="تاریخ تولد")
    national_code = models.CharField(
        max_length=10,
        unique=True,
        validators=[validate_national_code],
        verbose_name="کد ملی",
    )
    mobile = models.CharField(
        max_length=11,
        unique=True,
        validators=[validate_iranian_mobile],
        verbose_name="تلفن همراه",
    )

    # Supplementary Info (Desktop-3)
    province = models.CharField(max_length=100, verbose_name="استان محل سکونت")
    city = models.CharField(max_length=100, verbose_name="شهر محل سکونت")
    address = models.TextField(verbose_name="آدرس دقیق محل سکونت")
    postal_code = models.CharField(
        max_length=10,
        validators=[validate_postal_code],
        verbose_name="کد پستی",
    )
    bale_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="شناسه پیام‌رسان بله",
    )
    telegram_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="شناسه پیام‌رسان تلگرام",
    )

    # Profile & Status
    profile_picture = models.ImageField(
        upload_to="profiles/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="تصویر پروفایل",
    )
    is_mobile_verified = models.BooleanField(default=True, verbose_name="وضعیت تایید موبایل")

    # Permissions & Django Standard Fields
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_staff = models.BooleanField(default=False, verbose_name="دسترسی کارمند")

    objects = UserManager()

    USERNAME_FIELD = "national_code"
    REQUIRED_FIELDS = ["mobile", "first_name", "last_name", "birth_date", "job"]

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        indexes = [
            models.Index(fields=["mobile"]),
            models.Index(fields=["national_code"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.national_code})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
