from django.urls import path

from .views import (
    DashboardMobileChangeRequestView,
    DashboardMobileChangeVerifyView,
    DashboardProfileView,
    DashboardWorkDetailView,
    DashboardWorkListCreateView,
)

urlpatterns = [
    path("profile/", DashboardProfileView.as_view(), name="dashboard-profile"),
    path("profile/mobile/request/", DashboardMobileChangeRequestView.as_view(), name="dashboard-mobile-request"),
    path("profile/mobile/verify/", DashboardMobileChangeVerifyView.as_view(), name="dashboard-mobile-verify"),
    path("works/", DashboardWorkListCreateView.as_view(), name="dashboard-works-list"),
    path("works/<int:pk>/", DashboardWorkDetailView.as_view(), name="dashboard-works-detail"),
]
