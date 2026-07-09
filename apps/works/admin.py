from django.contrib import admin, messages
from django.http import FileResponse
from django.utils.html import format_html

from .models import Work
from .services import AdminZipExportService


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "image_preview",
        "get_user_info",
        "short_description",
        "original_filename",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "user__national_code",
        "user__mobile",
        "user__first_name",
        "user__last_name",
        "description",
        "original_filename",
    )
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "image_preview_large")

    actions = ["export_selected_works_zip"]

    fieldsets = (
        (None, {
            "fields": ("user", "image", "original_filename", "description"),
        }),
        ("پیش‌نمایش تصویر", {
            "fields": ("image_preview_large",),
        }),
        ("اطلاعات سیستم", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="پیش‌نمایش", ordering="id")
    def image_preview(self, obj):
        if obj.image:
            url = obj.image.url
            img_tag = (
                f'<img src="{url}" style="width:50px;height:50px;'
                f'object-fit:cover;border-radius:4px;" />'
            )
            return format_html(f'<a href="{url}" target="_blank">{img_tag}</a>')
        return "—"

    @admin.display(description="پیش‌نمایش بزرگ")
    def image_preview_large(self, obj):
        if obj.image:
            url = obj.image.url
            img_tag = (
                f'<img src="{url}" style="width:100%;border-radius:8px;" />'
            )
            return format_html(
                f'<div style="max-width:400px;">'
                f'<a href="{url}" target="_blank">{img_tag}</a></div>'
            )
        return "—"

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
