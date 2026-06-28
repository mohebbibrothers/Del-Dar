import logging

from rest_framework import generics, permissions, status, views
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.sms.services import OTPService
from apps.sms.tasks import send_otp_sms_task
from apps.works.models import Work

from .serializers import (
    DashboardMobileChangeRequestSerializer,
    DashboardMobileChangeVerifySerializer,
    DashboardProfileSerializer,
    DashboardWorkCreateUpdateSerializer,
    DashboardWorkSerializer,
)
from .services import DashboardProfileService

logger = logging.getLogger(__name__)


class DashboardProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DashboardProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        user = self.request.user
        target_mobile = serializer.validated_data.get("mobile", user.mobile)
        if target_mobile != user.mobile:
            serializer.save(is_mobile_verified=True)
            DashboardProfileService.clear_verified_mobile_cache(user.id)
            logger.info("User ID %s successfully updated mobile to %s", user.id, target_mobile)
        else:
            serializer.save()


class DashboardMobileChangeRequestView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DashboardMobileChangeRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        new_mobile = serializer.validated_data["new_mobile"]

        code = OTPService.generate_otp()
        OTPService.set_otp(new_mobile, code, purpose=f"mobile_change_{request.user.id}")
        send_otp_sms_task.delay(new_mobile, code)

        return Response(
            {
                "success": True,
                "message": "کد تایید برای شماره همراه جدید پیامک شد",
                "new_mobile": new_mobile,
            }
        )


class DashboardMobileChangeVerifyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DashboardMobileChangeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_mobile = serializer.validated_data["new_mobile"]
        code = serializer.validated_data["otp_code"]

        purpose = f"mobile_change_{request.user.id}"
        is_valid = OTPService.verify_otp(new_mobile, code, purpose=purpose)
        if not is_valid:
            return Response(
                {"success": False, "error": "کد تایید اشتباه یا منقضی شده است"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        DashboardProfileService.mark_mobile_as_verified(request.user.id, new_mobile)
        return Response(
            {
                "success": True,
                "message": "شماره همراه جدید تایید شد؛ اکنون دکمه ثبت تغییرات را بزنید",
                "verified_mobile": new_mobile,
            }
        )


class DashboardWorkListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Work.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DashboardWorkCreateUpdateSerializer
        return DashboardWorkSerializer

    def create(self, request, *args, **kwargs):
        if Work.objects.filter(user=request.user).count() >= 50:
            return Response(
                {"success": False, "error": "شما حداکثر ۵۰ اثر مجاز را ارسال کرده‌اید"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        work = serializer.save(user=request.user)
        output_serializer = DashboardWorkSerializer(work)
        return Response(
            {"success": True, "message": "اثر با موفقیت ارسال شد", "work": output_serializer.data},
            status=status.HTTP_201_CREATED,
        )


class DashboardWorkDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Work.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return DashboardWorkCreateUpdateSerializer
        return DashboardWorkSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        output_serializer = DashboardWorkSerializer(instance)
        return Response(
            {"success": True, "message": "اثر ارسالی ویرایش شد", "work": output_serializer.data}
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.image:
            instance.image.delete(save=False)
        self.perform_destroy(instance)
        return Response(
            {"success": True, "message": "اثر ارسالی با موفقیت حذف شد"},
            status=status.HTTP_200_OK,
        )
