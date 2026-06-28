from django.urls import path

from .views import AuthLoginRequestView, AuthLoginVerifyView

urlpatterns = [
    path("login/request/", AuthLoginRequestView.as_view(), name="auth-login-request"),
    path("login/verify/", AuthLoginVerifyView.as_view(), name="auth-login-verify"),
]
