import logging

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_LARGER_DIMENSION_PX = 1000


def validate_work_image(image_file) -> None:
    # 1. Check file size
    if image_file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError("حجم فایل ارسالی نباید بیشتر از ۵ مگابایت باشد.")

    try:
        image_file.seek(0)
        with Image.open(image_file) as img:
            # 2. Verify it's a valid image (PIL will raise UnidentifiedImageError if not)
            # PIL supports: JPEG, PNG, WEBP, TIFF, GIF, BMP, HEIC/HEIF, etc.
            if not img.format:
                raise ValidationError("فرمت فایل ارسالی معتبر نیست.")

            # 3. Check the larger dimension (width for landscape, height for portrait)
            width, height = img.size
            larger_dimension = max(width, height)

            if larger_dimension < MIN_LARGER_DIMENSION_PX:
                raise ValidationError(
                    f"ابعاد تصویر ({width}×{height}px) استاندارد نیست؛ "
                    f"ضلع بزرگتر تصویر باید حداقل {MIN_LARGER_DIMENSION_PX} پیکسل باشد."
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
