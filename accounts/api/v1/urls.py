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
    PatientListCreateView,
    PatientDetailView,
    PatientNoteListCreateView,
    OverviewListCreateView,
    OverviewDetailView,
)

app_name = "accounts"

urlpatterns = [
    # ==========================================================
    # AUTHENTICATION
    # ==========================================================
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("auth/set-password/", SetPasswordView.as_view(), name="set_password"),

    # ==========================================================
    # USER PROFILE
    # ==========================================================
    path("me/", MeView.as_view(), name="me"),
    path("profile/", UserProfileView.as_view(), name="profile"),

    # ==========================================================
    # PATIENT
    # ==========================================================
    path("patients/", PatientListCreateView.as_view(), name="patient-list-create"),
    path("patients/<int:pk>/", PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<int:patient_id>/notes/", PatientNoteListCreateView.as_view(), name="patient-note-list-create"),

    # ==========================================================
    # OVERVIEW
    # ==========================================================
    path("patients/<int:patient_id>/overviews/", OverviewListCreateView.as_view(), name="overview-list-create"),
    path("overviews/<int:pk>/", OverviewDetailView.as_view(), name="overview-detail"),
]