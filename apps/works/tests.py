import io
import zipfile

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.works.models import Work
from apps.works.services import AdminZipExportService
from apps.works.validators import validate_work_image


def _create_test_image(format_name="JPEG", width=1200, height=1200):
    buffer = io.BytesIO()
    img = Image.new("RGB", (width, height), color="red")
    img.save(buffer, format=format_name)
    buffer.seek(0)
    ext = "jpg" if format_name == "JPEG" else format_name.lower()
    return SimpleUploadedFile(f"test.{ext}", buffer.read(), content_type=f"image/{ext}")


@pytest.mark.django_db
class TestWorkValidationAndModel:
    def test_valid_image_passes(self):
        img_file = _create_test_image("JPEG", 1200, 1200)
        validate_work_image(img_file)  # Should not raise

    def test_invalid_format_png_fails(self):
        img_file = _create_test_image("PNG", 1200, 1200)
        with pytest.raises(ValidationError):
            validate_work_image(img_file)

    def test_invalid_dimensions_too_small(self):
        img_file = _create_test_image("JPEG", 800, 800)
        with pytest.raises(ValidationError):
            validate_work_image(img_file)

    def test_create_work_record(self):
        user = User.objects.create_user(
            national_code="0123456789",
            mobile="09199999999",
            first_name="سارا",
            last_name="رضایی",
            job="هنرجو",
            birth_date="1995-05-05",
            province="اصفهان",
            city="اصفهان",
            address="میدان نقش جهان",
            postal_code="8888888888",
        )
        img_file = _create_test_image("JPEG", 1200, 1200)
        work = Work.objects.create(user=user, image=img_file, description="تصویر پرتره خورشید")
        assert work.user == user
        assert work.description == "تصویر پرتره خورشید"

        # Test single user ZIP export
        qs = User.objects.filter(id=user.id)
        zip_path, zip_name = AdminZipExportService.create_users_export_zip(qs)
        assert zip_name.startswith("deldar_users_export_")

        with zipfile.ZipFile(zip_path, "r") as zf:
            file_list = zf.namelist()
            assert "profile.txt" in file_list
            assert "1/description.txt" in file_list
            assert "1/image.jpg" in file_list

            profile_content = zf.read("profile.txt").decode("utf-8")
            assert "0123456789" in profile_content
            assert "سارا" in profile_content
            assert "رضایی" in profile_content
