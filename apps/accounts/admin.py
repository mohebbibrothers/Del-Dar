from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django.http import FileResponse

from apps.core.jalali_admin import JalaliAdminDateField
from apps.works.services import AdminZipExportService

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "national_code",
        "mobile",
        "first_name",
        "last_name",
        "get_works_count",
        "is_mobile_verified",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_mobile_verified", "is_staff", "is_superuser", "province")
    search_fields = ("national_code", "mobile", "first_name", "last_name", "postal_code")
    ordering = ("-created_at",)
    actions = ["export_users_works_zip"]

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
    formfield_overrides = {
        models.DateField: {"form_class": JalaliAdminDateField},
    }
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

    @admin.display(description="تعداد آثار ارسالی")
    def get_works_count(self, obj):
        return obj.works.count()

    @admin.action(description="خروجی ZIP از مشخصات و گالری آثار کاربران انتخاب‌شده")
    def export_users_works_zip(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "هیچ کاربری انتخاب نشده است", level=messages.WARNING)
            return None

        zip_filepath, zip_filename = AdminZipExportService.create_users_export_zip(queryset)
        return FileResponse(
            open(zip_filepath, "rb"), as_attachment=True, filename=zip_filename
        )
