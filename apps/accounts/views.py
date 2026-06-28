import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.sms.services import OTPService
from apps.sms.tasks import send_otp_sms_task

from .serializers import AuthLoginRequestSerializer, AuthLoginVerifySerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthLoginRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="درخواست پیامک ورود (OTP) با موبایل یا کدملی",
        description="کاربران ثبت‌نام‌شده، شماره موبایل ۱۱ رقمی یا کدملی ۱۰ رقمی خود را ارسال می‌کنند. در صورت معتبر بودن اکانت، یک کد تایید ۴ رقمی پیامک می‌شود.",
        request=AuthLoginRequestSerializer,
        examples=[
            OpenApiExample(
                "مثال ارسال موبایل",
                value={"identifier": "09121111111"},
                request_only=True,
            ),
            OpenApiExample(
                "مثال ارسال کدملی",
                value={"identifier": "0123456789"},
                request_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="ارسال موفق پیامک",
                examples=[
                    OpenApiExample(
                        "پاسخ موفق",
                        value={
                            "success": True,
                            "message": "کد ورود برای شماره همراه شما ارسال شد",
                            "mobile": "09121111111",
                        },
                    )
                ],
            ),
            404: OpenApiResponse(
                description="کاربر یافت نشد",
                examples=[
                    OpenApiExample(
                        "خطای عدم ثبت‌نام",
                        value={
                            "success": False,
                            "error": "کاربری با این تلفن همراه یا کد ملی ثبت نشده است",
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = AuthLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ident = serializer.validated_data["identifier"]

        user = User.objects.filter(Q(mobile=ident) | Q(national_code=ident)).first()
        if not user:
            return Response(
                {"success": False, "error": "کاربری با این تلفن همراه یا کد ملی ثبت نشده است"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            return Response(
                {"success": False, "error": "حساب کاربری شما غیرفعال شده است"},
                status=status.HTTP_403_FORBIDDEN,
            )

        code = OTPService.generate_otp()
        OTPService.set_otp(user.mobile, code, purpose="auth_login")
        send_otp_sms_task.delay(user.mobile, code)

        return Response(
            {
                "success": True,
                "message": "کد ورود برای شماره همراه شما ارسال شد",
                "mobile": user.mobile,
            }
        )


class AuthLoginVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="تایید کد ورود و دریافت توکن‌های JWT",
        description="کد ورود ۴ رقمی به همراه شناسه کاربری ارسال می‌شود. پس از تایید موفق، توکن دسترسی (Access) و رفرش (Refresh) صادر می‌شود.",
        request=AuthLoginVerifySerializer,
        examples=[
            OpenApiExample(
                "مثال ورودی",
                value={"identifier": "09121111111", "otp_code": "1234"},
                request_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                description="ورود موفقیت‌آمیز",
                examples=[
                    OpenApiExample(
                        "پاسخ موفق",
                        value={
                            "success": True,
                            "message": "ورود موفقیت‌آمیز بود",
                            "tokens": {
                                "access": "eyJhbGciOi...",
                                "refresh": "eyJhbGciOi...",
                            },
                            "user": {
                                "national_code": "0123456789",
                                "full_name": "علی محمدی",
                                "mobile": "09121111111",
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="کد اشتباه است",
                examples=[
                    OpenApiExample(
                        "خطای کد نامعتبر",
                        value={"success": False, "error": "کد ورود اشتباه است یا منقضی شده"},
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = AuthLoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ident = serializer.validated_data["identifier"]
        code = serializer.validated_data["otp_code"]

        user = User.objects.filter(Q(mobile=ident) | Q(national_code=ident)).first()
        if not user:
            return Response({"success": False, "error": "کاربر یافت نشد"}, status=404)

        is_valid = OTPService.verify_otp(user.mobile, code, purpose="auth_login")
        if not is_valid:
            return Response(
                {"success": False, "error": "کد ورود اشتباه است یا منقضی شده"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jwt_refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "ورود موفقیت‌آمیز بود",
                "tokens": {
                    "access": str(jwt_refresh.access_token),
                    "refresh": str(jwt_refresh),
                },
                "user": {
                    "national_code": user.national_code,
                    "full_name": user.full_name,
                    "mobile": user.mobile,
                },
            }
        )
