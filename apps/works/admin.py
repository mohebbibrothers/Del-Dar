from django.contrib import admin

from .models import Work


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

    @admin.display(description="صاحب اثر", ordering="user__national_code")
    def get_user_info(self, obj):
        return f"{obj.user.full_name} ({obj.user.national_code})"

    @admin.display(description="خلاصه کپشن")
    def short_description(self, obj):
        return obj.description[:50] + ("..." if len(obj.description) > 50 else "")
