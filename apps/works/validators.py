import logging

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_DIMENSION_PX = 1000
MAX_DIMENSION_PX = 1500


def validate_work_image(image_file) -> None:
    if image_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError("حجم فایل ارسالی نباید بیشتر از ۵ مگابایت باشد.")

    try:
        image_file.seek(0)
        with Image.open(image_file) as img:
            format_name = img.format.upper() if img.format else ""
            if format_name not in ("JPEG", "JPG"):
                raise ValidationError("فرمت فایل ارسالی معتبر نیست؛ صرفاً فرمت JPG پذیرفته می‌شود.")

            width, height = img.size
            if not (MIN_DIMENSION_PX <= width <= MAX_DIMENSION_PX):
                raise ValidationError(
                    f"عرض تصویر ({width}px) استاندارد نیست؛ ابعاد باید بین ۱۰۰۰ تا ۱۵۰۰ پیکسل باشد."
                )

            if not (MIN_DIMENSION_PX <= height <= MAX_DIMENSION_PX):
                raise ValidationError(
                    f"ارتفاع ({height}px) استاندارد نیست؛ ابعاد باید بین ۱۰۰۰ تا ۱۵۰۰ پیکسل باشد."
                )
    except UnidentifiedImageError as exc:
        raise ValidationError("فایل ارسالی خراب است و به عنوان تصویر شناسایی نشد.") from exc
    except ValidationError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error occurred while inspecting image metadata")
        raise ValidationError("خطایی در بررسی مشخصات فنی تصویر رخ داد.") from exc
    finally:
        if hasattr(image_file, "seek"):
            image_file.seek(0)
