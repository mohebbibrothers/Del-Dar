import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import permissions, status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.sms.services import OTPService
from apps.sms.tasks import send_otp_sms_task, send_welcome_sms_task
from apps.works.models import Work

from .serializers import (
    DraftWorkUploadSerializer,
    OTPVerifySerializer,
    Step1PersonalInfoSerializer,
    Step2SupplementaryInfoSerializer,
)
from .services import DraftOnboardingService

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_token_from_request(request) -> str:
    return request.headers.get("X-Draft-Token", "")


class DraftStateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = _get_token_from_request(request)
        draft = DraftOnboardingService.get_draft(token)
        return Response({"success": True, "draft": draft, "draft_token": token})


class Step1PersonalInfoView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = Step1PersonalInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = _get_token_from_request(request)
        new_token, draft = DraftOnboardingService.init_or_update_draft(
            token, {"personal_info": serializer.validated_data}
        )

        response = Response(
            {"success": True, "message": "اطلاعات شخصی با موفقیت ثبت شد", "draft": draft}
        )
        response["X-Draft-Token"] = new_token
        return response


class Step2SupplementaryInfoView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = Step2SupplementaryInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = _get_token_from_request(request)
        if not token:
            return Response(
                {"success": False, "error": "شناسه پیش‌نویس (X-Draft-Token) یافت نشد"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, draft = DraftOnboardingService.init_or_update_draft(
            token, {"supplementary_info": serializer.validated_data}
        )
        return Response(
            {"success": True, "message": "اطلاعات تکمیلی با موفقیت ثبت شد", "draft": draft}
        )


class DraftWorkUploadView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = _get_token_from_request(request)
        if not token:
            return Response(
                {"success": False, "error": "ابتدا مراحل قبل را تکمیل کنید"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        draft = DraftOnboardingService.get_draft(token)
        if len(draft.get("works", [])) >= 50:
            return Response(
                {"success": False, "error": "سقف ارسال ۵۰ اثر تکمیل شده است"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DraftWorkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        img_file = serializer.validated_data["image"]
        desc = serializer.validated_data["description"]

        work_id = str(uuid.uuid4())
        ext = img_file.name.split(".")[-1] if "." in img_file.name else "jpg"
        saved_path = default_storage.save(f"drafts/{token}/{work_id}.{ext}", img_file)

        work_item = {
            "id": work_id,
            "file_path": saved_path,
            "description": desc,
        }
        updated_draft = DraftOnboardingService.add_work(token, work_item)

        return Response(
            {"success": True, "message": "اثر به پیش‌نویس اضافه شد", "draft": updated_draft},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, work_id):
        token = _get_token_from_request(request)
        if not token:
            return Response({"success": False, "error": "توکن یافت نشد"}, status=400)

        draft = DraftOnboardingService.get_draft(token)
        target = next((w for w in draft.get("works", []) if w["id"] == work_id), None)
        if target and default_storage.exists(target["file_path"]):
            default_storage.delete(target["file_path"])

        updated_draft = DraftOnboardingService.remove_work(token, work_id)
        return Response({"success": True, "draft": updated_draft})


class OnboardingSubmitView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = _get_token_from_request(request)
        draft = DraftOnboardingService.get_draft(token)

        personal = draft.get("personal_info", {})
        supp = draft.get("supplementary_info", {})
        works = draft.get("works", [])

        if not personal.get("mobile") or not personal.get("national_code"):
            return Response(
                {"success": False, "error": "اطلاعات شخصی (مرحله ۱) ناقص است"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not supp.get("province") or not supp.get("city"):
            return Response(
                {"success": False, "error": "اطلاعات تکمیلی (مرحله ۲) ناقص است"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not works:
            return Response(
                {"success": False, "error": "حداقل ارسال یک اثر الزامی است"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mobile = personal["mobile"]
        code = OTPService.generate_otp()
        OTPService.set_otp(mobile, code, purpose="onboarding")
        send_otp_sms_task.delay(mobile, code)

        return Response(
            {"success": True, "message": "کد تایید برای شماره شما ارسال شد", "mobile": mobile}
        )


class OnboardingVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["otp_code"]

        token = _get_token_from_request(request)
        draft = DraftOnboardingService.get_draft(token)
        personal = draft.get("personal_info", {})
        supp = draft.get("supplementary_info", {})
        works_list = draft.get("works", [])

        mobile = personal.get("mobile")
        if not mobile:
            return Response({"success": False, "error": "پیش‌نویس منقضی یا ناقص است"}, status=400)

        is_valid = OTPService.verify_otp(mobile, code, purpose="onboarding")
        if not is_valid:
            return Response({"success": False, "error": "کد وارد شده صحیح نیست"}, status=400)

        with transaction.atomic():
            user = User.objects.create_user(
                national_code=personal["national_code"],
                mobile=mobile,
                first_name=personal["first_name"],
                last_name=personal["last_name"],
                job=personal["job"],
                birth_date=personal["birth_date"],
                province=supp["province"],
                city=supp["city"],
                address=supp["address"],
                postal_code=supp["postal_code"],
                bale_id=supp.get("bale_id"),
                telegram_id=supp.get("telegram_id"),
                is_mobile_verified=True,
            )

            for item in works_list:
                Work.objects.create(
                    user=user,
                    image=item["file_path"],
                    description=item["description"],
                )

        DraftOnboardingService.clear_draft(token)
        send_welcome_sms_task.delay(mobile)

        jwt_refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "ثبت‌نام با موفقیت انجام شد و اکانت شما ایجاد گردید",
                "tokens": {
                    "access": str(jwt_refresh.access_token),
                    "refresh": str(jwt_refresh),
                },
                "user": {
                    "national_code": user.national_code,
                    "full_name": user.full_name,
                    "mobile": user.mobile,
                },
            },
            status=status.HTTP_201_CREATED,
        )
