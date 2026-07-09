from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel

from .validators import validate_work_image

MAX_WORKS_PER_USER = 50


class Work(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="works",
        verbose_name="صاحب اثر",
    )
    image = models.ImageField(
        upload_to="works/%Y/%m/",
        validators=[validate_work_image],
        verbose_name="فایل تصویر",
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="نام اصلی فایل",
    )
    description = models.TextField(verbose_name="توضیحات و کپشن اثر")

    class Meta:
        verbose_name = "اثر عکاسی"
        verbose_name_plural = "آثار عکاسی"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["user", "created_at", "id"]),
        ]

    def __str__(self):
        return f"Work #{self.id} by {self.user.national_code}"

    def clean(self):
        super().clean()
        if not self.pk and self.user_id:
            current_count = Work.objects.filter(user_id=self.user_id).count()
            if current_count >= MAX_WORKS_PER_USER:
                raise ValidationError(
                    f"هر کاربر حداکثر مجاز به ارسال {MAX_WORKS_PER_USER} اثر می‌باشد."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
