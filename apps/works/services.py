import logging
import os
import uuid
import zipfile

import jdatetime
from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class AdminZipExportService:
    @classmethod
    def create_users_export_zip(cls, users_queryset) -> tuple[str, str]:
        export_id = str(uuid.uuid4())
        export_dir = settings.MEDIA_ROOT / "temp_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_filename = f"deldar_users_export_{export_id[:8]}.zip"
        zip_filepath = export_dir / zip_filename

        is_bulk = users_queryset.count() > 1
        logger.info(
            "Starting admin ZIP export for %d user(s). Target: %s",
            users_queryset.count(),
            zip_filepath,
        )

        with zipfile.ZipFile(zip_filepath, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for user in users_queryset.prefetch_related("works").iterator(chunk_size=50):
                safe_name = f"{user.first_name}_{user.last_name}".replace(" ", "_")
                user_folder = f"{user.national_code}_{safe_name}" if is_bulk else ""

                # 1. Profile document
                profile_text = cls._format_user_profile_text(user)
                profile_path = (
                    os.path.join(user_folder, "profile.txt") if user_folder else "profile.txt"
                )
                zf.writestr(profile_path, profile_text.encode("utf-8"))

                # 2. User works
                for idx, work in enumerate(user.works.all(), start=1):
                    work_folder = (
                        os.path.join(user_folder, str(idx)) if user_folder else str(idx)
                    )

                    # description.txt
                    desc_path = os.path.join(work_folder, "description.txt")
                    zf.writestr(desc_path, (work.description or "").encode("utf-8"))

                    # image content
                    if work.image and default_storage.exists(work.image.name):
                        ext = (
                            work.image.name.split(".")[-1]
                            if "." in work.image.name
                            else "jpg"
                        )
                        img_path = os.path.join(work_folder, f"image.{ext}")
                        with default_storage.open(work.image.name, "rb") as img_file:
                            zf.writestr(img_path, img_file.read())

        return str(zip_filepath), zip_filename

    @classmethod
    def create_works_export_zip(cls, works_queryset) -> tuple[str, str]:
        export_id = str(uuid.uuid4())
        export_dir = settings.MEDIA_ROOT / "temp_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_filename = f"deldar_works_export_{export_id[:8]}.zip"
        zip_filepath = export_dir / zip_filename

        iterator = works_queryset.select_related("user").iterator(chunk_size=100)
        with zipfile.ZipFile(zip_filepath, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for _idx, work in enumerate(iterator, start=1):
                user = work.user
                folder_name = f"work_{work.id}_{user.national_code}"

                # description.txt
                head = f"عکاس: {user.full_name} ({user.national_code})"
                desc_text = f"{head}\nکپشن:\n{work.description}"
                zf.writestr(
                    os.path.join(folder_name, "description.txt"),
                    desc_text.encode("utf-8"),
                )

                # image
                if work.image and default_storage.exists(work.image.name):
                    ext = (
                        work.image.name.split(".")[-1]
                        if "." in work.image.name
                        else "jpg"
                    )
                    with default_storage.open(work.image.name, "rb") as img_file:
                        arc_path = os.path.join(folder_name, f"content.{ext}")
                        zf.writestr(arc_path, img_file.read())

        return str(zip_filepath), zip_filename

    @staticmethod
    def _format_user_profile_text(user) -> str:
        if user.birth_date:
            jd_birth = jdatetime.date.fromgregorian(date=user.birth_date)
            jalali_birth = f"{jd_birth.year}/{jd_birth.month:02d}/{jd_birth.day:02d}"
        else:
            jalali_birth = "---"

        jd_c = jdatetime.datetime.fromgregorian(datetime=user.created_at)
        time_str = f"{jd_c.hour:02d}:{jd_c.minute:02d}"
        jalali_created = f"{jd_c.year}/{jd_c.month:02d}/{jd_c.day:02d} {time_str}"

        lines = [
            "==================================================",
            "           پرونده جامع اطلاعات شرکت‌کننده          ",
            "==================================================",
            f"نام: {user.first_name}",
            f"نام خانوادگی: {user.last_name}",
            f"کد ملی: {user.national_code}",
            f"تلفن همراه: {user.mobile}",
            f"وضعیت تایید موبایل: {'تایید شده' if user.is_mobile_verified else 'تایید نشده'}",
            f"شغل: {user.job}",
            f"تاریخ تولد (جلالی): {jalali_birth}",
            "--------------------------------------------------",
            f"استان محل سکونت: {user.province}",
            f"شهر محل سکونت: {user.city}",
            f"آدرس پستی دقیق: {user.address}",
            f"کد پستی ۱۰ رقمی: {user.postal_code}",
            f"شناسه پیام‌رسان بله: {user.bale_id or '---'}",
            f"شناسه پیام‌رسان تلگرام: {user.telegram_id or '---'}",
            "--------------------------------------------------",
            f"تعداد آثار ثبت‌شده در گالری: {user.works.count()}",
            f"تاریخ ثبت‌نام در سیستم: {jalali_created}",
            "==================================================",
        ]
        return "\n".join(lines)
