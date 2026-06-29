import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
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


class DraftStateView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        summary="دریافت وضعیت کامل کش پیش‌نویس ثبت‌نام",
        description="با ارسال هدر X-Draft-Token، تمامی اطلاعات واردشده در فرم‌های ۱، ۲ و لیست عکس‌های آپلودشده بازگشت داده می‌شود تا کاربر نیاز به تایپ مجدد نداشته باشد.",
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                description="توکن یکتای پیش‌نویس تولیدشده در مرحله اول",
            )
        ],
        responses={
            200: OpenApiResponse(
                description="بازخوانی موفق کش",
                examples=[
                    OpenApiExample(
                        "نمونه پیش‌نویس فعال",
                        value={
                            "success": True,
                            "draft_token": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                            "draft": {
                                "personal_info": {
                                    "first_name": "امیر",
                                    "last_name": "رضایی",
                                    "mobile": "09121111111",
                                    "national_code": "0123456789",
                                },
                                "supplementary_info": {"province": "تهران", "city": "تهران"},
                                "works": [
                                    {
                                        "id": "work_uuid_1",
                                        "file_path": "drafts/...",
                                        "description": "کپشن اثر",
                                    }
                                ],
                            },
                        },
                    )
                ],
            )
        },
    )
    def get(self, request):
        token = _get_token_from_request(request)
        draft = DraftOnboardingService.get_draft(token)
        return Response({"success": True, "draft": draft, "draft_token": token})


class Step1PersonalInfoView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = Step1PersonalInfoSerializer

    @extend_schema(
        summary="ثبت اطلاعات شخصی (مرحله اول ثبت‌نام مهمان)",
        description="دریافت ۶ فیلد اطلاعات فردی. نکته مهم سناریوی بازگشت به عقب: اگر کاربر برای اولین بار وارد این متد می‌شود هدر X-Draft-Token را ارسال نمی‌کند؛ اما هنگام بازگشت به عقب جهت ویرایش شماره موبایل، ارسال این هدر الزامی است تا اطلاعات فرم‌های بعد نپرد.",
        request=Step1PersonalInfoSerializer,
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description="توکن کش پیش‌نویس (اختیاری در بار اول؛ الزامی هنگام ویرایش بازگشت به عقب)",
            )
        ],
        examples=[
            OpenApiExample(
                "ورودی استاندارد مرحله ۱",
                value={
                    "first_name": "سارا",
                    "last_name": "احمدی",
                    "job": "معمار داخلی",
                    "birth_date": "1992-04-10",
                    "national_code": "0123456789",
                    "mobile": "09123334455",
                },
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(description="ثبت در کش و صدور توکن پیش‌نویس"),
            400: OpenApiResponse(description="خطای تکراری بودن کدملی یا موبایل"),
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
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


class Step2SupplementaryInfoView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = Step2SupplementaryInfoSerializer

    @extend_schema(
        summary="ثبت اطلاعات تکمیلی سکونت و شبکه‌های اجتماعی (مرحله دوم ثبت‌نام)",
        description="دریافت استان، شهر، آدرس دقیق، کدپستی ۱۰ رقمی و شناسه‌های بله و تلگرام (اختیاری). ارسال هدر X-Draft-Token الزامی است.",
        request=Step2SupplementaryInfoSerializer,
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
        examples=[
            OpenApiExample(
                "ورودی استاندارد مرحله ۲",
                value={
                    "province": "اصفهان",
                    "city": "اصفهان",
                    "address": "خیابان چهارباغ عباسی، کوچه آمادگاه، پلاک ۱۲",
                    "postal_code": "8123456789",
                    "bale_id": "@sara_arch",
                    "telegram_id": "@sara_photo",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
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


class DraftWorkUploadView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DraftWorkUploadSerializer

    @extend_schema(
        summary="آپلود تصویر اثر در پیش‌نویس (مرحله سوم ثبت‌نام)",
        description="آپلود عکس با فرمت multipart/form-data. محدودیت‌های فنی: فرمت صرفاً JPG، حجم حداکثر ۵ مگابایت و ابعاد بین ۱۰۰۰ تا ۱۵۰۰ پیکسل. کپشن اثر الزامی است.",
        request=DraftWorkUploadSerializer,
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
        responses={201: OpenApiResponse(description="افزودن موفق اثر به پیش‌نویس")},
    )
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

        serializer = self.get_serializer(data=request.data)
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


class DraftWorkDeleteView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        summary="حذف تصویر از پیش‌نویس ثبت‌نام",
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
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


class OnboardingSubmitView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    @extend_schema(
        summary="ارسال نهایی ۳ فرم ثبت‌نام و درخواست پیامک OTP",
        description="بررسی زنده اینکه مرحله ۱، مرحله ۲ و حداقل ۱ اثر در مرحله ۳ تکمیل شده باشند. سپس یک کد تایید ۴ رقمی برای موبایل کاربر پیامک می‌شود.",
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                description="ارسال موفق کد",
                examples=[
                    OpenApiExample(
                        "پاسخ تایید پیامک",
                        value={
                            "success": True,
                            "message": "کد تایید برای شماره شما ارسال شد",
                            "mobile": "09123334455",
                        },
                    )
                ],
            )
        },
    )
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


class OnboardingVerifyView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPVerifySerializer

    @extend_schema(
        summary="تایید کد OTP، ساخت نهایی اکانت و ورود خودکار",
        description="کد تایید وارد می‌شود. در تراکنش اتمیک دیتابیس، اکانت کاربر ایجاد شده، آثار از کش به دیتابیس منتقل شده و توکن‌های ورود خودکار (JWT Access & Refresh) صادر می‌گردد.",
        request=OTPVerifySerializer,
        parameters=[
            OpenApiParameter(
                name="X-Draft-Token",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
        examples=[
            OpenApiExample(
                "ورودی تایید ثبت‌نام",
                value={"otp_code": "1234"},
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                description="ثبت‌نام قطعی و لاگین موفق",
                examples=[
                    OpenApiExample(
                        "پاسخ صدور اکانت",
                        value={
                            "success": True,
                            "message": "ثبت‌نام با موفقیت انجام شد و اکانت شما ایجاد گردید",
                            "tokens": {
                                "access": "eyJhbGciOi...",
                                "refresh": "eyJhbGciOi...",
                            },
                            "user": {
                                "national_code": "0123456789",
                                "full_name": "سارا احمدی",
                                "mobile": "09123334455",
                            },
                        },
                    )
                ],
            )
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
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
