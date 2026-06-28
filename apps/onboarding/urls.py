from django.urls import path

from .views import (
    DraftStateView,
    DraftWorkUploadView,
    OnboardingSubmitView,
    OnboardingVerifyView,
    Step1PersonalInfoView,
    Step2SupplementaryInfoView,
)

urlpatterns = [
    path("draft/", DraftStateView.as_view(), name="onboarding-draft"),
    path("step-1/", Step1PersonalInfoView.as_view(), name="onboarding-step1"),
    path("step-2/", Step2SupplementaryInfoView.as_view(), name="onboarding-step2"),
    path("works/", DraftWorkUploadView.as_view(), name="onboarding-works"),
    path("works/<str:work_id>/", DraftWorkUploadView.as_view(), name="onboarding-works-delete"),
    path("submit/", OnboardingSubmitView.as_view(), name="onboarding-submit"),
    path("verify/", OnboardingVerifyView.as_view(), name="onboarding-verify"),
]
