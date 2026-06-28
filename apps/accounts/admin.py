from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "national_code",
        "mobile",
        "first_name",
        "last_name",
        "is_mobile_verified",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_mobile_verified", "is_staff", "is_superuser", "province")
    search_fields = ("national_code", "mobile", "first_name", "last_name", "postal_code")
    ordering = ("-created_at",)

    fieldsets = (
        ("احراز هویت اصلی", {"fields": ("national_code", "mobile", "password")}),
        (
            "اطلاعات شخصی",
            {"fields": ("first_name", "last_name", "job", "birth_date", "profile_picture")},
        ),
        (
            "اطلاعات تکمیلی سکونت و ارتباطی",
            {
                "fields": (
                    "province",
                    "city",
                    "address",
                    "postal_code",
                    "bale_id",
                    "telegram_id",
                )
            },
        ),
        (
            "وضعیت سیستم",
            {
                "fields": (
                    "is_mobile_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "national_code",
                    "mobile",
                    "first_name",
                    "last_name",
                    "job",
                    "birth_date",
                    "province",
                    "city",
                    "address",
                    "postal_code",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
