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
                works = list(user.works.all().order_by("created_at", "id"))
                safe_name = f"{user.first_name}_{user.last_name}".replace(" ", "_")
                user_folder = f"{user.national_code}_{safe_name}" if is_bulk else ""

                # 1. Profile document
                profile_text = cls._format_user_profile_text(user)
                profile_path = (
                    os.path.join(user_folder, "profile.txt") if user_folder else "profile.txt"
                )
                zf.writestr(profile_path, profile_text.encode("utf-8"))

                if not works:
                    continue

                # 2. Gallery folder with new naming convention
                gallery_folder = (
                    os.path.join(user_folder, f"gallery_{len(works)}")
                    if user_folder
                    else f"gallery_{len(works)}"
                )

                for idx, work in enumerate(works, start=1):
                    if not work.image or not default_storage.exists(work.image.name):
                        continue

                    original_filename = cls._resolve_filename(work)
                    base_name = f"{idx}_{original_filename}"

                    # image file: 1_book.jpg
                    img_path = os.path.join(gallery_folder, base_name)
                    with default_storage.open(work.image.name, "rb") as img_file:
                        zf.writestr(img_path, img_file.read())

                    # description file: 1_book.txt
                    desc_path = os.path.join(gallery_folder, f"{base_name}.txt")
                    zf.writestr(desc_path, (work.description or "").encode("utf-8"))

        return str(zip_filepath), zip_filename

    @classmethod
    def create_works_export_zip(cls, works_queryset) -> tuple[str, str]:
        export_id = str(uuid.uuid4())
        export_dir = settings.MEDIA_ROOT / "temp_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_filename = f"deldar_works_export_{export_id[:8]}.zip"
        zip_filepath = export_dir / zip_filename

        works = works_queryset.select_related("user").order_by("created_at", "id")

        with zipfile.ZipFile(zip_filepath, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for _idx, work in enumerate(works.iterator(chunk_size=100), start=1):
                user = work.user
                original_filename = cls._resolve_filename(work)
                folder_name = f"work_{work.id}_{user.national_code}"

                # image with original name
                if work.image and default_storage.exists(work.image.name):
                    with default_storage.open(work.image.name, "rb") as img_file:
                        arc_path = os.path.join(folder_name, original_filename)
                        zf.writestr(arc_path, img_file.read())

                # description
                head = f"عکاس: {user.full_name} ({user.national_code})"
                desc_text = f"{head}\nکپشن:\n{work.description}"
                zf.writestr(
                    os.path.join(folder_name, f"{original_filename}.txt"),
                    desc_text.encode("utf-8"),
                )

        return str(zip_filepath), zip_filename

    @staticmethod
    def _resolve_filename(work) -> str:
        """
        Get the display filename for a work.
        Priority: 1) original_filename field, 2) basename from storage path.
        """
        if work.original_filename:
            return work.original_filename
        return os.path.basename(work.image.name) if work.image else "unknown.jpg"

    @classmethod
    def _format_user_profile_text(cls, user) -> str:
        birth_text = "---"
        if user.birth_date:
            # Check if birth_date was stored as Jalali date misinterpreted as Gregorian
            # If year is between 1300-1500, it's likely a Jalali date stored as Gregorian
            if 1300 <= user.birth_date.year <= 1500:
                # It's already in Jalali format, just use it directly
                jd_birth = jdatetime.date(
                    user.birth_date.year, user.birth_date.month, user.birth_date.day
                )
            else:
                jd_birth = jdatetime.date.fromgregorian(date=user.birth_date)
            birth_text = f"{jd_birth.year}/{jd_birth.month:02d}/{jd_birth.day:02d}"

        if 1300 <= user.created_at.year <= 1500:
            jd_c = jdatetime.datetime(
                user.created_at.year,
                user.created_at.month,
                user.created_at.day,
                user.created_at.hour,
                user.created_at.minute,
            )
        else:
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
            f"تاریخ تولد: {birth_text}",
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
