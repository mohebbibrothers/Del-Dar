from django.contrib import admin, messages
from django.http import FileResponse

from .models import Work
from .services import AdminZipExportService


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("id", "get_user_info", "short_description", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "user__national_code",
        "user__mobile",
        "user__first_name",
        "user__last_name",
        "description",
    )
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    actions = ["export_selected_works_zip"]

    @admin.display(description="صاحب اثر", ordering="user__national_code")
    def get_user_info(self, obj):
        return f"{obj.user.full_name} ({obj.user.national_code})"

    @admin.display(description="خلاصه کپشن")
    def short_description(self, obj):
        return obj.description[:50] + ("..." if len(obj.description) > 50 else "")

    @admin.action(description="خروجی ZIP اختصاصی از تصاویر انتخاب‌شده")
    def export_selected_works_zip(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "هیچ اثری انتخاب نشده است", level=messages.WARNING)
            return None

        zip_path, zip_name = AdminZipExportService.create_works_export_zip(queryset)
        return FileResponse(open(zip_path, "rb"), as_attachment=True, filename=zip_name)
