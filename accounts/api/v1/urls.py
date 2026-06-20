from django.urls import path
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    SendOTPView,
    VerifyOTPView,
    SetPasswordView,
    MeView,
    UserProfileView,
)

app_name = "accounts"

urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="register"),

    # JWT Token
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),

    # OTP Authentication
    path("auth/send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),

    # Password Management
    path("auth/set-password/", SetPasswordView.as_view(), name="set_password"),

    # User Profile
    path("me/", MeView.as_view(), name="me"),
    path("profile/", UserProfileView.as_view(), name="profile"),
]