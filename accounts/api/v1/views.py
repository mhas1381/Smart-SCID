"""
API v1 views for accounts app.
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.cache import cache
from drf_spectacular.utils import extend_schema_view
import secrets
import time
import logging

from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    SetPasswordSerializer,
    UserMeSerializer,
    UserProfileSerializer,
)
from .openapi.schema import (
    register_schema,
    token_obtain_schema,
    token_refresh_schema,
    send_otp_schema,
    verify_otp_schema,
    set_password_schema,
    me_schema,
    profile_get_schema,
    profile_create_schema,
    profile_update_schema,
)
from ...models import UserProfile
from utils.sms import send_verification_code

User = get_user_model()
logger = logging.getLogger("accounts")

OTP_LENGTH = 5
CACHE_TIMEOUT = 120


# ============================================================
# REGISTER VIEW
# ============================================================

@extend_schema_view(
    post=register_schema,
)
class RegisterView(generics.CreateAPIView):
    """
    Register a new user with phone number and password.
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        try:
            profile = user.profile
            role = profile.role
            profile_image = profile.profile_image.url if profile.profile_image else None
        except UserProfile.DoesNotExist:
            role = "clinician"
            profile_image = None

        response_data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": role,
                "profile_image": profile_image,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "has_password": user.has_usable_password(),
            },
            "message": "ثبت نام با موفقیت انجام شد.",
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


# ============================================================
# JWT TOKEN VIEWS
# ============================================================

@extend_schema_view(
    post=token_obtain_schema,
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT Token Obtain Pair View.
    """
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    post=token_refresh_schema,
)
class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom JWT Token Refresh View.
    """
    pass


# ============================================================
# OTP VIEWS
# ============================================================

@extend_schema_view(
    post=send_otp_schema,
)
class SendOTPView(generics.GenericAPIView):
    """
    Send OTP to phone number for authentication.
    """
    permission_classes = [AllowAny]
    serializer_class = SendOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]

            cache_key = f"otp_{phone_number}"
            cached_data = cache.get(cache_key)

            if cached_data:
                expires_at = cached_data.get("expires_at")
                now = time.time()
                if expires_at and expires_at > now:
                    remaining_ttl = int(expires_at - now)
                    return Response(
                        {
                            "detail": f"کد فعال وجود دارد. {remaining_ttl} ثانیه دیگر تلاش کنید.",
                            "ttl": remaining_ttl
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            otp_code = "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))
            expires_at = time.time() + CACHE_TIMEOUT

            cache.set(cache_key, {"code": otp_code, "expires_at": expires_at}, timeout=CACHE_TIMEOUT)

            send_verification_code(phone_number, otp_code)

            user_exists = User.objects.filter(phone_number=phone_number).exists()

            return Response({
                "detail": "کد تایید ارسال شد.",
                "user_exists": user_exists,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=verify_otp_schema,
)
class VerifyOTPView(generics.GenericAPIView):
    """
    Verify OTP and authenticate user.
    """
    permission_classes = [AllowAny]
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            otp_code = serializer.validated_data["otp_code"]

            cache_key = f"otp_{phone_number}"
            cached_data = cache.get(cache_key)

            if not cached_data or cached_data.get("code") != otp_code:
                return Response(
                    {"detail": "کد تایید نامعتبر یا منقضی شده است."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cache.delete(cache_key)

            user = User.objects.filter(phone_number=phone_number).first()

            if not user:
                user = User.objects.create(
                    phone_number=phone_number,
                    is_active=True,
                )

            user.refresh_from_db()
            refresh = RefreshToken.for_user(user)

            try:
                profile = user.profile
                role = profile.role
                profile_image = profile.profile_image.url if profile.profile_image else None
            except UserProfile.DoesNotExist:
                role = "clinician"
                profile_image = None

            response_data = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "role": role,
                    "profile_image": profile_image,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "has_password": user.has_usable_password(),
                },
                "is_new_user": not user.has_usable_password(),
            }

            return Response(response_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# PASSWORD VIEWS
# ============================================================

@extend_schema_view(
    post=set_password_schema,
)
class SetPasswordView(generics.GenericAPIView):
    """
    Set password for authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            password = serializer.validated_data["password"]

            user.set_password(password)
            user.save()

            logger.info(f"Password set for user {user.id}")

            return Response(
                {"detail": "رمز عبور با موفقیت تنظیم شد."},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# USER PROFILE VIEWS
# ============================================================

@extend_schema_view(
    get=me_schema,
)
class MeView(generics.GenericAPIView):
    """
    Get authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserMeSerializer

    def get(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=profile_get_schema,
    post=profile_create_schema,
    put=profile_update_schema,
    patch=profile_update_schema,
)
class UserProfileView(generics.GenericAPIView):
    """
    Get, create or update user profile.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get(self, request):
        try:
            profile = request.user.profile
            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "پروفایل یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def post(self, request):
        try:
            profile = request.user.profile
            return Response(
                {"detail": "پروفایل قبلاً ایجاد شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except UserProfile.DoesNotExist:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                profile = serializer.save(user=request.user)
                return Response(
                    self.get_serializer(profile).data,
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "پروفایل یافت نشد. ابتدا پروفایل ایجاد کنید."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(self.get_serializer(profile).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "پروفایل یافت نشد. ابتدا پروفایل ایجاد کنید."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(self.get_serializer(profile).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)