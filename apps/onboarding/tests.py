import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.sms.services import OTPService
from apps.works.models import Work

User = get_user_model()


def _create_test_uploaded_img():
    buf = io.BytesIO()
    img = Image.new("RGB", (1200, 1200), color="blue")
    img.save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("sample.jpg", buf.read(), content_type="image/jpeg")


@pytest.mark.django_db
class TestOnboardingAndAuthFlows:
    def setup_method(self):
        self.client = APIClient()

    def test_full_onboarding_lifecycle(self):
        # Step 1
        step1_data = {
            "first_name": "پویا",
            "last_name": "حسینی",
            "job": "طراح گرافیک",
            "birth_date": "1992-02-02",
            "national_code": "0123456789",
            "mobile": "09361112233",
        }
        res1 = self.client.post("/api/v1/onboarding/step-1/", step1_data, format="json")
        assert res1.status_code == 200
        draft_token = res1.headers["X-Draft-Token"]
        assert draft_token

        # Step 2
        self.client.credentials(HTTP_X_DRAFT_TOKEN=draft_token)
        step2_data = {
            "province": "خراسان رضوی",
            "city": "مشهد",
            "address": "بلوار سجاد",
            "postal_code": "9188888888",
            "bale_id": "@pouya_bale",
        }
        res2 = self.client.post("/api/v1/onboarding/step-2/", step2_data, format="json")
        assert res2.status_code == 200

        # Upload draft work
        work_data = {
            "image": _create_test_uploaded_img(),
            "description": "عکاسی معماری حرم",
        }
        res_work = self.client.post("/api/v1/onboarding/works/", work_data, format="multipart")
        assert res_work.status_code == 201
        assert len(res_work.data["draft"]["works"]) == 1

        # Submit triggers OTP
        res_sub = self.client.post("/api/v1/onboarding/submit/", {}, format="json")
        assert res_sub.status_code == 200

        # Get generated OTP code
        otp_code = OTPService.get_otp("09361112233", purpose="onboarding")
        assert otp_code

        # Verify
        res_ver = self.client.post(
            "/api/v1/onboarding/verify/", {"otp_code": otp_code}, format="json"
        )
        assert res_ver.status_code == 201
        assert "tokens" in res_ver.data
        assert res_ver.data["user"]["national_code"] == "0123456789"

        # Database verification
        user_db = User.objects.get(national_code="0123456789")
        assert user_db.is_mobile_verified is True
        assert Work.objects.filter(user=user_db).count() == 1

    def test_login_flow(self):
        # Create user
        user = User.objects.create_user(
            national_code="1234567891",
            mobile="09158887766",
            first_name="زهرا",
            last_name="کاظمی",
            job="مستند ساز",
            birth_date="1988-08-08",
            province="فارس",
            city="شیراز",
            address="خیابان ارم",
            postal_code="7188888888",
        )

        res_req = self.client.post(
            "/api/v1/auth/login/request/", {"identifier": "1234567891"}, format="json"
        )
        assert res_req.status_code == 200

        code = OTPService.get_otp(user.mobile, purpose="auth_login")
        res_ver = self.client.post(
            "/api/v1/auth/login/verify/",
            {"identifier": "1234567891", "otp_code": code},
            format="json",
        )
        assert res_ver.status_code == 200
        assert "tokens" in res_ver.data
