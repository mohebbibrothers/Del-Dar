import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.sms.services import OTPService
from apps.works.models import Work

User = get_user_model()


def _create_test_img():
    buf = io.BytesIO()
    img = Image.new("RGB", (1200, 1200), color="green")
    img.save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("dash.jpg", buf.read(), content_type="image/jpeg")


@pytest.mark.django_db
class TestDashboardAPIs:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            national_code="0123456789",
            mobile="09121111111",
            first_name="علیرضا",
            last_name="شریفی",
            job="خبرنگار",
            birth_date="1985-01-01",
            province="تهران",
            city="تهران",
            address="خیابان ولیعصر",
            postal_code="1111111111",
        )
        self.client.force_authenticate(user=self.user)

    def test_profile_retrieve_and_standard_update(self):
        res_get = self.client.get("/api/v1/dashboard/profile/")
        assert res_get.status_code == 200
        assert res_get.data["first_name"] == "علیرضا"

        # Update job without changing mobile
        update_data = {
            "first_name": "علیرضا",
            "last_name": "شریفی",
            "job": "سردبیر عکس",
            "birth_date": "1985-01-01",
            "national_code": "0123456789",
            "mobile": "09121111111",
            "province": "تهران",
            "city": "تهران",
            "address": "خیابان ولیعصر",
            "postal_code": "1111111111",
        }
        res_put = self.client.put("/api/v1/dashboard/profile/", update_data, format="json")
        assert res_put.status_code == 200
        self.user.refresh_from_db()
        assert self.user.job == "سردبیر عکس"

    def test_mobile_change_requires_verification(self):
        update_data = {
            "first_name": "علیرضا",
            "last_name": "شریفی",
            "job": "خبرنگار",
            "birth_date": "1985-01-01",
            "national_code": "0123456789",
            "mobile": "09129999999",  # Unverified change
            "province": "تهران",
            "city": "تهران",
            "address": "خیابان ولیعصر",
            "postal_code": "1111111111",
        }
        res_put = self.client.put("/api/v1/dashboard/profile/", update_data, format="json")
        assert res_put.status_code == 400
        assert "ابتدا شماره تلفن همراه خود را تایید کنید" in str(res_put.data)

        # Trigger mobile OTP flow
        res_req = self.client.post("/api/v1/dashboard/profile/mobile/request/", {"new_mobile": "09129999999"}, format="json")
        assert res_req.status_code == 200

        otp = OTPService.get_otp("09129999999", purpose=f"mobile_change_{self.user.id}")
        res_ver = self.client.post("/api/v1/dashboard/profile/mobile/verify/", {"new_mobile": "09129999999", "otp_code": otp}, format="json")
        assert res_ver.status_code == 200

        # Now PUT should succeed
        res_put_ok = self.client.put("/api/v1/dashboard/profile/", update_data, format="json")
        assert res_put_ok.status_code == 200
        self.user.refresh_from_db()
        assert self.user.mobile == "09129999999"

    def test_works_crud(self):
        work_data = {"image": _create_test_img(), "description": "ثبت طبیعت گلستان"}
        res_create = self.client.post("/api/v1/dashboard/works/", work_data, format="multipart")
        assert res_create.status_code == 201
        work_id = res_create.data["work"]["id"]

        # Edit description
        res_patch = self.client.patch(f"/api/v1/dashboard/works/{work_id}/", {"description": "طبیعت پاییزی گلستان"}, format="json")
        assert res_patch.status_code == 200
        assert Work.objects.get(id=work_id).description == "طبیعت پاییزی گلستان"

        # Delete work
        res_del = self.client.delete(f"/api/v1/dashboard/works/{work_id}/")
        assert res_del.status_code == 200
        assert Work.objects.filter(id=work_id).exists() is False
