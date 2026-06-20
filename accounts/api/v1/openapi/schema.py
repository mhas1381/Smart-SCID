"""
OpenAPI schema definitions for accounts API v1.
"""

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    inline_serializer,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers


# ============================================================
# AUTHENTICATION SCHEMAS
# ============================================================

register_schema = extend_schema(
    summary="📝 Register New User",
    tags=["🔐 Authentication"],
    description="""
    Register a new user with phone number and password.
    
    **📋 Required fields:**
    ✅ `phone_number` - Iranian mobile number (09XXXXXXXXX)
    ✅ `password` - min 8 chars, include number, letter, special char
    ✅ `confirm_password` - must match password
    
    **🔸 Optional fields:**
    ⭕ `first_name` - User's first name
    ⭕ `last_name` - User's last name
    ⭕ `email` - User's email address
    
    **⚠️ Notes:**
    - Phone number must be exactly 11 digits starting with 09
    - Password must contain at least one number, letter, and special character
    - Default role for new users is 'clinician'
    - Profile is automatically created via signals
    """,
    request=inline_serializer(
        name="RegisterRequest",
        fields={
            "phone_number": serializers.CharField(required=True),
            "password": serializers.CharField(required=True, write_only=True),
            "confirm_password": serializers.CharField(required=True, write_only=True),
            "first_name": serializers.CharField(required=False, allow_blank=True),
            "last_name": serializers.CharField(required=False, allow_blank=True),
            "email": serializers.EmailField(required=False, allow_blank=True, allow_null=True),
        },
    ),
    responses={
        201: inline_serializer(
            name="RegisterResponse",
            fields={
                "refresh": serializers.CharField(),
                "access": serializers.CharField(),
                "user": inline_serializer(
                    name="RegisterUser",
                    fields={
                        "id": serializers.IntegerField(),
                        "phone_number": serializers.CharField(),
                        "first_name": serializers.CharField(),
                        "last_name": serializers.CharField(),
                        "email": serializers.CharField(allow_null=True),
                        "role": serializers.CharField(),
                        "profile_image": serializers.CharField(allow_null=True),
                        "is_staff": serializers.BooleanField(),
                        "is_superuser": serializers.BooleanField(),
                        "has_password": serializers.BooleanField(),
                    },
                ),
                "message": serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Register Request",
            value={
                "phone_number": "09123456789",
                "password": "Test@1234",
                "confirm_password": "Test@1234",
                "first_name": "احمد",
                "last_name": "رضایی",
                "email": "ahmad@example.com",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Register Response (Success)",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIs...",
                "access": "eyJhbGciOiJIUzI1NiIs...",
                "user": {
                    "id": 1,
                    "phone_number": "09123456789",
                    "first_name": "احمد",
                    "last_name": "رضایی",
                    "email": "ahmad@example.com",
                    "role": "clinician",
                    "profile_image": None,
                    "is_staff": False,
                    "is_superuser": False,
                    "has_password": True,
                },
                "message": "ثبت نام با موفقیت انجام شد.",
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Error - Duplicate Phone",
            value={
                "phone_number": ["کاربری با این شماره تلفن قبلاً ثبت نام کرده است."],
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Error - Password Mismatch",
            value={
                "confirm_password": ["رمز عبور و تکرار آن یکسان نیستند."],
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Error - Invalid Phone Format",
            value={
                "phone_number": ["شماره تلفن همراه باید با 09 شروع شود و ۱۱ رقم باشد."],
            },
            response_only=True,
        ),
    ],
)


send_otp_schema = extend_schema(
    summary="📱 Send OTP",
    tags=["🔐 Authentication"],
    description="""
    Send a 5-digit OTP verification code to the provided phone number.
    
    **📋 Required fields:**
    ✅ `phone_number` - Iranian mobile number (09XXXXXXXXX)
    
    **⚡ Features:**
    🛡️ Rate limited: One OTP per 2 minutes per phone number
    ⏱️ OTP expires after 2 minutes
    🔍 Returns whether the user already exists in the system
    
    **💻 Development Mode:**
    📝 OTP is printed in console instead of being sent via SMS
    
    **⚠️ Note:**
    If an active OTP exists, you must wait for it to expire before requesting a new one.
    """,
    request=inline_serializer(
        name="SendOTPRequest",
        fields={
            "phone_number": serializers.CharField(required=True),
        },
    ),
    responses={
        200: inline_serializer(
            name="SendOTPResponse",
            fields={
                "detail": serializers.CharField(),
                "user_exists": serializers.BooleanField(),
            },
        ),
        400: inline_serializer(
            name="SendOTPError",
            fields={
                "detail": serializers.CharField(),
                "ttl": serializers.IntegerField(required=False),
            },
        ),
    },
    examples=[
        OpenApiExample(
            "📤 Send OTP Request",
            value={
                "phone_number": "09123456789",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Send OTP Response (New User)",
            value={
                "detail": "کد تایید ارسال شد.",
                "user_exists": False,
            },
            response_only=True,
        ),
        OpenApiExample(
            "✅ Send OTP Response (Existing User)",
            value={
                "detail": "کد تایید ارسال شد.",
                "user_exists": True,
            },
            response_only=True,
        ),
        OpenApiExample(
            "⏳ Rate Limited Response",
            value={
                "detail": "کد فعال وجود دارد. 90 ثانیه دیگر تلاش کنید.",
                "ttl": 90,
            },
            response_only=True,
        ),
    ],
)


verify_otp_schema = extend_schema(
    summary="✅ Verify OTP",
    tags=["🔐 Authentication"],
    description="""
    Verify the OTP code and authenticate the user.
    
    **📋 Required fields:**
    ✅ `phone_number` - Phone number that received the OTP
    ✅ `otp_code` - 5-digit verification code
    
    **👤 For existing users:**
    🔑 Returns JWT tokens immediately
    🚀 User can login and access the system
    
    **🆕 For new users:**
    📝 Creates a new user account automatically
    🔑 Returns JWT tokens
    ⚠️ `has_password` will be **False** - user must set password via `/auth/set-password/`
    
    **⚠️ Important:**
    - OTP is valid for only 2 minutes
    - OTP is deleted after successful verification
    - One-time use only
    """,
    request=inline_serializer(
        name="VerifyOTPRequest",
        fields={
            "phone_number": serializers.CharField(required=True),
            "otp_code": serializers.CharField(required=True),
        },
    ),
    responses={
        200: inline_serializer(
            name="VerifyOTPResponse",
            fields={
                "refresh": serializers.CharField(),
                "access": serializers.CharField(),
                "user": inline_serializer(
                    name="VerifyOTPUser",
                    fields={
                        "id": serializers.IntegerField(),
                        "phone_number": serializers.CharField(),
                        "first_name": serializers.CharField(),
                        "last_name": serializers.CharField(),
                        "email": serializers.CharField(allow_null=True),
                        "role": serializers.CharField(),
                        "profile_image": serializers.CharField(allow_null=True),
                        "is_staff": serializers.BooleanField(),
                        "is_superuser": serializers.BooleanField(),
                        "has_password": serializers.BooleanField(),
                    },
                ),
                "is_new_user": serializers.BooleanField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Verify OTP Request",
            value={
                "phone_number": "09123456789",
                "otp_code": "12345",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Verify OTP Response (Existing User)",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIs...",
                "access": "eyJhbGciOiJIUzI1NiIs...",
                "user": {
                    "id": 1,
                    "phone_number": "09123456789",
                    "first_name": "احمد",
                    "last_name": "رضایی",
                    "email": "ahmad@example.com",
                    "role": "clinician",
                    "profile_image": None,
                    "is_staff": False,
                    "is_superuser": False,
                    "has_password": True,
                },
                "is_new_user": False,
            },
            response_only=True,
        ),
        OpenApiExample(
            "🆕 Verify OTP Response (New User)",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIs...",
                "access": "eyJhbGciOiJIUzI1NiIs...",
                "user": {
                    "id": 2,
                    "phone_number": "09123456789",
                    "first_name": "",
                    "last_name": "",
                    "email": None,
                    "role": "clinician",
                    "profile_image": None,
                    "is_staff": False,
                    "is_superuser": False,
                    "has_password": False,
                },
                "is_new_user": True,
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Invalid OTP Response",
            value={
                "detail": "کد تایید نامعتبر یا منقضی شده است.",
            },
            response_only=True,
        ),
    ],
)


set_password_schema = extend_schema(
    summary="🔑 Set Password",
    tags=["🔐 Authentication"],
    description="""
    Set or update password for authenticated user.
    
    **📋 Required fields:**
    ✅ `password` - New password (min 8 chars, include number, letter, special char)
    ✅ `confirm_password` - Must match password
    
    **👤 Use Cases:**
    🆕 New users who registered via OTP
    🔄 Users who want to change their password
    🔓 Users who forgot password (after OTP verification)
    
    **🔐 Requirements:**
    🛡️ User must be authenticated (JWT token required)
    🔒 Password must be strong
    """,
    request=inline_serializer(
        name="SetPasswordRequest",
        fields={
            "password": serializers.CharField(required=True, write_only=True),
            "confirm_password": serializers.CharField(required=True, write_only=True),
        },
    ),
    responses={
        200: inline_serializer(
            name="SetPasswordResponse",
            fields={
                "detail": serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Set Password Request",
            value={
                "password": "NewStrong@Pss123",
                "confirm_password": "NewStrong@Pss123",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Set Password Response",
            value={
                "detail": "رمز عبور با موفقیت تنظیم شد.",
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Error - Password Mismatch",
            value={
                "confirm_password": ["رمز عبور و تکرار آن یکسان نیستند."],
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Error - Weak Password",
            value={
                "password": ["رمز عبور باید حداقل شامل یک حرف انگلیسی باشد."],
            },
            response_only=True,
        ),
    ],
)


token_obtain_schema = extend_schema(
    summary="🔑 Login with Phone & Password",
    tags=["🔐 Authentication"],
    description="""
    Authenticate user using phone number and password.
    
    **📋 Required fields:**
    ✅ `phone_number` - Registered phone number
    ✅ `password` - User password
    
    **🔑 Returns:**
    🎫 JWT access and refresh tokens
    👤 User information (id, name, role, etc.)
    
    **⚠️ Note:**
    - Use the access token in `Authorization: Bearer <token>` header for authenticated requests
    - Refresh token can be used to get a new access token when it expires
    """,
    request=inline_serializer(
        name="TokenObtainRequest",
        fields={
            "phone_number": serializers.CharField(required=True),
            "password": serializers.CharField(required=True, write_only=True),
        },
    ),
    responses={
        200: inline_serializer(
            name="TokenObtainResponse",
            fields={
                "refresh": serializers.CharField(),
                "access": serializers.CharField(),
                "user": inline_serializer(
                    name="TokenObtainUser",
                    fields={
                        "id": serializers.IntegerField(),
                        "phone_number": serializers.CharField(),
                        "first_name": serializers.CharField(),
                        "last_name": serializers.CharField(),
                        "email": serializers.CharField(allow_null=True),
                        "role": serializers.CharField(),
                        "profile_image": serializers.CharField(allow_null=True),
                        "is_staff": serializers.BooleanField(),
                        "is_superuser": serializers.BooleanField(),
                        "has_password": serializers.BooleanField(),
                    },
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Login Request",
            value={
                "phone_number": "09123456789",
                "password": "Test@1234",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Login Response",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIs...",
                "access": "eyJhbGciOiJIUzI1NiIs...",
                "user": {
                    "id": 1,
                    "phone_number": "09123456789",
                    "first_name": "احمد",
                    "last_name": "رضایی",
                    "email": "ahmad@example.com",
                    "role": "clinician",
                    "profile_image": None,
                    "is_staff": False,
                    "is_superuser": False,
                    "has_password": True,
                },
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Invalid Credentials",
            value={
                "detail": "No active account found with the given credentials",
            },
            response_only=True,
        ),
    ],
)


token_refresh_schema = extend_schema(
    summary="🔄 Refresh Access Token",
    tags=["🔐 Authentication"],
    description="""
    Get a new access token using refresh token.
    
    **📋 Required fields:**
    ✅ `refresh` - Valid refresh token
    
    **🔑 Returns:**
    🎫 New access token
    🎫 New refresh token
    
    **⚠️ Note:**
    - Refresh token is valid for 7 days
    - Use this endpoint when access token expires
    - Old refresh token is rotated (new one is issued)
    """,
    request=inline_serializer(
        name="TokenRefreshRequest",
        fields={
            "refresh": serializers.CharField(required=True),
        },
    ),
    responses={
        200: inline_serializer(
            name="TokenRefreshResponse",
            fields={
                "access": serializers.CharField(),
                "refresh": serializers.CharField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Refresh Request",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIs...",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Refresh Response",
            value={
                "access": "eyJhbGciOiJIUzI1NiIs...",
                "refresh": "eyJhbGciOiJIUzI1NiIs...",
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Invalid Refresh Token",
            value={
                "detail": "Token is invalid or expired",
                "code": "token_not_valid",
            },
            response_only=True,
        ),
    ],
)


# ============================================================
# USER PROFILE SCHEMAS
# ============================================================

me_schema = extend_schema(
    summary="👤 Get Current User",
    tags=["👤 User Profile"],
    description="""
    Get detailed information about the currently authenticated user.
    
    **🔑 Returns:**
    👤 User information including profile data and role
    🖼️ Profile image URL (if set)
    🏷️ User role (admin, clinician, researcher)
    
    **🔐 Requirements:**
    🛡️ JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="MeResponse",
            fields={
                "id": serializers.IntegerField(),
                "phone_number": serializers.CharField(),
                "first_name": serializers.CharField(),
                "last_name": serializers.CharField(),
                "email": serializers.CharField(allow_null=True),
                "role": serializers.CharField(),
                "profile_image": serializers.CharField(allow_null=True),
                "is_staff": serializers.BooleanField(),
                "is_superuser": serializers.BooleanField(),
                "has_password": serializers.BooleanField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "👤 Clinician Profile",
            value={
                "id": 1,
                "phone_number": "09123456789",
                "first_name": "احمد",
                "last_name": "رضایی",
                "email": "ahmad@example.com",
                "role": "clinician",
                "profile_image": None,
                "is_staff": False,
                "is_superuser": False,
                "has_password": True,
            },
            response_only=True,
        ),
        OpenApiExample(
            "👤 Admin Profile",
            value={
                "id": 2,
                "phone_number": "09123456789",
                "first_name": "مدیر",
                "last_name": "سیستم",
                "email": "admin@example.com",
                "role": "admin",
                "profile_image": "/media/profiles/admin.jpg",
                "is_staff": True,
                "is_superuser": True,
                "has_password": True,
            },
            response_only=True,
        ),
        OpenApiExample(
            "👤 Researcher Profile",
            value={
                "id": 3,
                "phone_number": "09123456789",
                "first_name": "پژوهشگر",
                "last_name": "نمونه",
                "email": "researcher@example.com",
                "role": "researcher",
                "profile_image": None,
                "is_staff": False,
                "is_superuser": False,
                "has_password": True,
            },
            response_only=True,
        ),
    ],
)


profile_get_schema = extend_schema(
    summary="📋 Get User Profile",
    tags=["👤 User Profile"],
    description="""
    Get detailed user profile including professional information.
    
    **📋 Profile Fields:**
    👤 Personal: birth_date, gender, national_code
    💼 Professional: role, license_number, specialization, organization, years_of_experience
    🖼️ Media: profile_image
    📅 Metadata: created_at, updated_at
    
    **🔐 Requirements:**
    🛡️ JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="ProfileResponse",
            fields={
                "id": serializers.IntegerField(),
                "user": serializers.IntegerField(),
                "full_name": serializers.CharField(),
                "phone_number": serializers.CharField(),
                "birth_date": serializers.CharField(allow_null=True),
                "gender": serializers.CharField(allow_null=True),
                "national_code": serializers.CharField(allow_null=True),
                "role": serializers.CharField(),
                "license_number": serializers.CharField(),
                "specialization": serializers.CharField(),
                "organization": serializers.CharField(),
                "years_of_experience": serializers.IntegerField(allow_null=True),
                "profile_image": serializers.CharField(allow_null=True),
                "created_at": serializers.CharField(),
                "updated_at": serializers.CharField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📋 Profile Response",
            value={
                "id": 1,
                "user": 1,
                "full_name": "احمد رضایی",
                "phone_number": "09123456789",
                "birth_date": "1990-01-15",
                "gender": "male",
                "national_code": "1234567890",
                "role": "clinician",
                "license_number": "12345",
                "specialization": "Clinical Psychology",
                "organization": "Tehran Clinic",
                "years_of_experience": 5,
                "profile_image": None,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z",
            },
            response_only=True,
        ),
    ],
)


profile_create_schema = extend_schema(
    summary="➕ Create User Profile",
    tags=["👤 User Profile"],
    description="""
    Create a new profile for authenticated user.
    
    **📋 Optional fields:**
    ⭕ `birth_date` - User's birth date (YYYY-MM-DD)
    ⭕ `gender` - male, female, other
    ⭕ `national_code` - 10-digit Iranian national code
    ⭕ `role` - admin, clinician, researcher (default: clinician)
    ⭕ `license_number` - Professional license number
    ⭕ `specialization` - Clinical specialization
    ⭕ `organization` - Workplace name
    ⭕ `years_of_experience` - Years of professional experience
    ⭕ `profile_image` - Profile picture (multipart/form-data)
    
    **⚠️ Note:**
    Profile is automatically created via signals when user registers.
    This endpoint is only needed if profile was not created automatically.
    """,
    request=inline_serializer(
        name="ProfileCreateRequest",
        fields={
            "birth_date": serializers.DateField(required=False, allow_null=True),
            "gender": serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_null=True),
            "national_code": serializers.CharField(required=False, allow_null=True),
            "role": serializers.ChoiceField(choices=["admin", "clinician", "researcher"], required=False),
            "license_number": serializers.CharField(required=False, allow_blank=True),
            "specialization": serializers.CharField(required=False, allow_blank=True),
            "organization": serializers.CharField(required=False, allow_blank=True),
            "years_of_experience": serializers.IntegerField(required=False, allow_null=True),
        },
    ),
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Create Profile Request",
            value={
                "birth_date": "1990-01-15",
                "gender": "male",
                "national_code": "1234567890",
                "role": "clinician",
                "license_number": "12345",
                "specialization": "Clinical Psychology",
                "organization": "Tehran Clinic",
                "years_of_experience": 5,
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Create Profile Response",
            value={
                "id": 1,
                "user": 1,
                "birth_date": "1990-01-15",
                "gender": "male",
                "national_code": "1234567890",
                "role": "clinician",
                "license_number": "12345",
                "specialization": "Clinical Psychology",
                "organization": "Tehran Clinic",
                "years_of_experience": 5,
                "profile_image": None,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z",
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Profile Already Exists",
            value={
                "detail": "پروفایل قبلاً ایجاد شده است.",
            },
            response_only=True,
        ),
    ],
)


profile_update_schema = extend_schema(
    summary="✏️ Update User Profile",
    tags=["👤 User Profile"],
    description="""
    Update user profile information.
    
    **🔸 For PUT (Full Update):**
    ⚠️ All fields are required
    
    **🔸 For PATCH (Partial Update):**
    ✅ Only send fields you want to update
    
    **📋 Available fields:**
    ⭕ `birth_date` - User's birth date
    ⭕ `gender` - male, female, other
    ⭕ `national_code` - 10-digit Iranian national code
    ⭕ `role` - admin, clinician, researcher
    ⭕ `license_number` - Professional license number
    ⭕ `specialization` - Clinical specialization
    ⭕ `organization` - Workplace name
    ⭕ `years_of_experience` - Years of experience
    ⭕ `profile_image` - Profile picture (multipart/form-data)
    
    **🔐 Requirements:**
    🛡️ JWT authentication required
    ⚠️ Profile must exist (create it first via POST /profile/)
    """,
    request=inline_serializer(
        name="ProfileUpdateRequest",
        fields={
            "birth_date": serializers.DateField(required=False, allow_null=True),
            "gender": serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_null=True),
            "national_code": serializers.CharField(required=False, allow_null=True),
            "role": serializers.ChoiceField(choices=["admin", "clinician", "researcher"], required=False),
            "license_number": serializers.CharField(required=False, allow_blank=True),
            "specialization": serializers.CharField(required=False, allow_blank=True),
            "organization": serializers.CharField(required=False, allow_blank=True),
            "years_of_experience": serializers.IntegerField(required=False, allow_null=True),
        },
    ),
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Update Profile Request (PATCH)",
            value={
                "specialization": "Neuropsychology",
                "years_of_experience": 7,
                "organization": "Tehran Neuroscience Institute",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Update Profile Response",
            value={
                "id": 1,
                "user": 1,
                "full_name": "احمد رضایی",
                "phone_number": "09123456789",
                "birth_date": "1990-01-15",
                "gender": "male",
                "national_code": "1234567890",
                "role": "clinician",
                "license_number": "12345",
                "specialization": "Neuropsychology",
                "organization": "Tehran Neuroscience Institute",
                "years_of_experience": 7,
                "profile_image": None,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-15T14:30:00Z",
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Profile Not Found",
            value={
                "detail": "پروفایل یافت نشد. ابتدا پروفایل ایجاد کنید.",
            },
            response_only=True,
        ),
    ],
)


# ============================================================
# PATIENT SCHEMAS
# ============================================================

patient_list_schema = extend_schema(
    summary="📋 List Patients",
    tags=["👤 Patients"],
    description="""
    Retrieve a list of all patients created by the authenticated clinician.
    
    **🔐 Requirements:**
    🛡️ JWT authentication required
    👤 Only returns patients created by the current user
    """,
    responses={
        200: inline_serializer(
            name="PatientListResponse",
            fields={
                "count": serializers.IntegerField(),
                "next": serializers.CharField(allow_null=True),
                "previous": serializers.CharField(allow_null=True),
                "results": serializers.ListField(
                    child=inline_serializer(
                        name="PatientListItem",
                        fields={
                            "id": serializers.IntegerField(),
                            "patient_code": serializers.CharField(),
                            "full_name": serializers.CharField(),
                            "phone_number": serializers.CharField(),
                            "gender": serializers.CharField(allow_null=True),
                            "birth_date": serializers.CharField(allow_null=True),
                            "created_by_name": serializers.CharField(),
                            "created_at": serializers.CharField(),
                            "is_active": serializers.BooleanField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
)


patient_create_schema = extend_schema(
    summary="➕ Create Patient",
    tags=["👤 Patients"],
    description="""
    Create a new patient record.
    
    **📋 Required fields:**
    ✅ `first_name` - Patient's first name
    ✅ `last_name` - Patient's last name
    
    **🔸 Optional fields:**
    ⭕ `phone_number` - Iranian mobile number (09XXXXXXXXX)
    ⭕ `email` - Email address
    ⭕ `national_code` - 10-digit Iranian national code
    ⭕ `birth_date` - Birth date (YYYY-MM-DD)
    ⭕ `gender` - male, female, other
    ⭕ `marital_status` - single, married, divorced, widowed
    ⭕ `education` - elementary, high_school, diploma, bachelor, master, doctoral
    ⭕ `occupation` - Patient's job
    ⭕ `address` - Full address
    ⭕ `emergency_contact_name` - Emergency contact person
    ⭕ `emergency_contact_phone` - Emergency contact phone
    """,
    request=inline_serializer(
        name="PatientCreateRequest",
        fields={
            "first_name": serializers.CharField(required=True),
            "last_name": serializers.CharField(required=True),
            "phone_number": serializers.CharField(required=False, allow_blank=True),
            "email": serializers.EmailField(required=False, allow_blank=True),
            "national_code": serializers.CharField(required=False, allow_blank=True),
            "birth_date": serializers.DateField(required=False, allow_null=True),
            "gender": serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_null=True),
            "marital_status": serializers.ChoiceField(choices=["single", "married", "divorced", "widowed"], required=False, allow_null=True),
            "education": serializers.ChoiceField(choices=["elementary", "middle_school", "high_school", "diploma", "associate", "bachelor", "master", "doctoral"], required=False, allow_null=True),
            "occupation": serializers.CharField(required=False, allow_blank=True),
            "address": serializers.CharField(required=False, allow_blank=True),
            "emergency_contact_name": serializers.CharField(required=False, allow_blank=True),
            "emergency_contact_phone": serializers.CharField(required=False, allow_blank=True),
        },
    ),
    responses={
        201: inline_serializer(
            name="PatientCreateResponse",
            fields={
                "id": serializers.IntegerField(),
                "patient_code": serializers.CharField(),
                "first_name": serializers.CharField(),
                "last_name": serializers.CharField(),
                "full_name": serializers.CharField(),
                "phone_number": serializers.CharField(),
                "message": serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
)


patient_detail_schema = extend_schema(
    summary="📄 Get Patient Details",
    tags=["👤 Patients"],
    description="""
    Get detailed information about a specific patient.
    """,
    responses={
        200: inline_serializer(
            name="PatientDetailResponse",
            fields={
                "id": serializers.IntegerField(),
                "patient_code": serializers.CharField(),
                "first_name": serializers.CharField(),
                "last_name": serializers.CharField(),
                "full_name": serializers.CharField(),
                "phone_number": serializers.CharField(),
                "email": serializers.CharField(),
                "national_code": serializers.CharField(),
                "birth_date": serializers.CharField(allow_null=True),
                "age": serializers.IntegerField(allow_null=True),
                "gender": serializers.CharField(allow_null=True),
                "marital_status": serializers.CharField(allow_null=True),
                "education": serializers.CharField(allow_null=True),
                "occupation": serializers.CharField(),
                "address": serializers.CharField(),
                "emergency_contact_name": serializers.CharField(),
                "emergency_contact_phone": serializers.CharField(),
                "created_by": serializers.IntegerField(),
                "created_by_name": serializers.CharField(),
                "created_at": serializers.CharField(),
                "updated_at": serializers.CharField(),
                "is_active": serializers.BooleanField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


patient_update_schema = extend_schema(
    summary="✏️ Update Patient",
    tags=["👤 Patients"],
    description="""
    Update patient information.
    
    **🔸 For PATCH (Partial Update):**
    ✅ Only send fields you want to update
    """,
    request=inline_serializer(
        name="PatientUpdateRequest",
        fields={
            "first_name": serializers.CharField(required=False),
            "last_name": serializers.CharField(required=False),
            "phone_number": serializers.CharField(required=False, allow_blank=True),
            "email": serializers.EmailField(required=False, allow_blank=True),
            "national_code": serializers.CharField(required=False, allow_blank=True),
            "birth_date": serializers.DateField(required=False, allow_null=True),
            "gender": serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_null=True),
            "marital_status": serializers.ChoiceField(choices=["single", "married", "divorced", "widowed"], required=False, allow_null=True),
            "education": serializers.ChoiceField(choices=["elementary", "middle_school", "high_school", "diploma", "associate", "bachelor", "master", "doctoral"], required=False, allow_null=True),
            "occupation": serializers.CharField(required=False, allow_blank=True),
            "address": serializers.CharField(required=False, allow_blank=True),
            "emergency_contact_name": serializers.CharField(required=False, allow_blank=True),
            "emergency_contact_phone": serializers.CharField(required=False, allow_blank=True),
            "is_active": serializers.BooleanField(required=False),
        },
    ),
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


patient_delete_schema = extend_schema(
    summary="🗑️ Delete Patient (Soft)",
    tags=["👤 Patients"],
    description="""
    Soft delete a patient (sets is_active=False).
    """,
    responses={
        204: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


patient_note_list_schema = extend_schema(
    summary="📋 List Patient Notes",
    tags=["👤 Patients"],
    description="""
    Retrieve all notes for a specific patient.
    """,
    responses={
        200: inline_serializer(
            name="PatientNoteListResponse",
            fields={
                "count": serializers.IntegerField(),
                "next": serializers.CharField(allow_null=True),
                "previous": serializers.CharField(allow_null=True),
                "results": serializers.ListField(
                    child=inline_serializer(
                        name="PatientNoteItem",
                        fields={
                            "id": serializers.IntegerField(),
                            "clinician_name": serializers.CharField(),
                            "note_type": serializers.CharField(),
                            "content": serializers.CharField(),
                            "created_at": serializers.CharField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


patient_note_create_schema = extend_schema(
    summary="➕ Add Patient Note",
    tags=["👤 Patients"],
    description="""
    Add a new note for a patient.
    
    **📋 Required fields:**
    ✅ `content` - Note content
    ✅ `note_type` - general, progress, follow_up, referral, other
    """,
    request=inline_serializer(
        name="PatientNoteCreateRequest",
        fields={
            "content": serializers.CharField(required=True),
            "note_type": serializers.ChoiceField(choices=["general", "progress", "follow_up", "referral", "other"], required=False, default="general"),
        },
    ),
    responses={
        201: inline_serializer(
            name="PatientNoteCreateResponse",
            fields={
                "id": serializers.IntegerField(),
                "clinician_name": serializers.CharField(),
                "note_type": serializers.CharField(),
                "content": serializers.CharField(),
                "created_at": serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


# ============================================================
# OVERVIEW SCHEMAS
# ============================================================

overview_list_schema = extend_schema(
    summary="📋 List Overviews",
    tags=["📋 Overview"],
    description="""
    Retrieve all overviews for a specific patient.
    """,
    responses={
        200: inline_serializer(
            name="OverviewListResponse",
            fields={
                "count": serializers.IntegerField(),
                "next": serializers.CharField(allow_null=True),
                "previous": serializers.CharField(allow_null=True),
                "results": serializers.ListField(
                    child=inline_serializer(
                        name="OverviewListItem",
                        fields={
                            "id": serializers.IntegerField(),
                            "patient": serializers.IntegerField(),
                            "patient_name": serializers.CharField(),
                            "clinician": serializers.IntegerField(),
                            "clinician_name": serializers.CharField(),
                            "age": serializers.IntegerField(allow_null=True),
                            "occupation": serializers.CharField(),
                            "suicide_attempt": serializers.BooleanField(),
                            "created_at": serializers.CharField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


overview_create_schema = extend_schema(
    summary="➕ Create Overview",
    tags=["📋 Overview"],
    description="""
    Create a new SCID-5-CV Overview for a patient.
    
    This includes all sections from the SCID-5-CV Overview:
    - Demographic Information
    - History of Current Illness
    - Treatment History
    - Medical Problems
    - Suicidal Ideation & Behavior
    - Other Current Problems
    """,
    request=inline_serializer(
        name="OverviewCreateRequest",
        fields={
            # Demographic Information
            "age": serializers.IntegerField(required=False, allow_null=True),
            "living_with": serializers.CharField(required=False, allow_blank=True),
            "living_place": serializers.CharField(required=False, allow_blank=True),
            "occupation": serializers.CharField(required=False, allow_blank=True),
            "occupation_history": serializers.CharField(required=False, allow_blank=True),
            "employment_status": serializers.CharField(required=False, allow_blank=True),
            "part_time_hours": serializers.IntegerField(required=False, allow_null=True),
            "part_time_reason": serializers.CharField(required=False, allow_blank=True),
            "unemployment_reason": serializers.CharField(required=False, allow_blank=True),
            "disability_payments": serializers.BooleanField(required=False, default=False),
            "disability_reason": serializers.CharField(required=False, allow_blank=True),
            "unable_to_work_history": serializers.BooleanField(required=False, default=False),
            "unable_to_work_reason": serializers.CharField(required=False, allow_blank=True),

            # History of Current Illness
            "presenting_problem": serializers.CharField(required=False, allow_blank=True),
            "onset_circumstances": serializers.CharField(required=False, allow_blank=True),
            "last_feeling_ok": serializers.CharField(required=False, allow_blank=True),

            # Treatment History
            "first_treatment_age": serializers.CharField(required=False, allow_blank=True),
            "first_treatment_reason": serializers.CharField(required=False, allow_blank=True),
            "psychiatric_hospitalization": serializers.BooleanField(required=False, default=False),
            "hospitalization_count": serializers.IntegerField(required=False, allow_null=True),
            "hospitalization_reason": serializers.CharField(required=False, allow_blank=True),
            "substance_treatment": serializers.BooleanField(required=False, default=False),
            "treatment_history": serializers.JSONField(required=False, default=list),

            # Medical Problems
            "physical_health": serializers.CharField(required=False, allow_blank=True),
            "medical_hospitalization": serializers.BooleanField(required=False, default=False),
            "medical_hospitalization_reason": serializers.CharField(required=False, allow_blank=True),
            "current_medications": serializers.CharField(required=False, allow_blank=True),

            # Suicidal Ideation & Behavior
            "wished_dead": serializers.BooleanField(required=False, default=False),
            "wished_dead_details": serializers.CharField(required=False, allow_blank=True),
            "thoughts_past_week": serializers.BooleanField(required=False, default=False),
            "strong_urge_past_week": serializers.BooleanField(required=False, default=False),
            "strong_urge_details": serializers.CharField(required=False, allow_blank=True),
            "intention_past_week": serializers.BooleanField(required=False, default=False),
            "intention_details": serializers.CharField(required=False, allow_blank=True),
            "plan_past_week": serializers.BooleanField(required=False, default=False),
            "plan_details": serializers.CharField(required=False, allow_blank=True),
            "suicide_attempt": serializers.BooleanField(required=False, default=False),
            "self_harm": serializers.BooleanField(required=False, default=False),
            "suicide_attempt_details": serializers.CharField(required=False, allow_blank=True),
            "most_severe_attempt": serializers.CharField(required=False, allow_blank=True),
            "attempt_past_week": serializers.BooleanField(required=False, default=False),

            # Other Current Problems
            "other_problems": serializers.CharField(required=False, allow_blank=True),
            "mood_description": serializers.CharField(required=False, allow_blank=True),
            "alcohol_use": serializers.CharField(required=False, allow_blank=True),
            "alcohol_with_whom": serializers.CharField(required=False, allow_blank=True),
            "drug_use": serializers.CharField(required=False, allow_blank=True),
        },
    ),
    responses={
        201: inline_serializer(
            name="OverviewCreateResponse",
            fields={
                "id": serializers.IntegerField(),
                "patient": serializers.IntegerField(),
                "clinician": serializers.IntegerField(),
                "message": serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


overview_detail_schema = extend_schema(
    summary="📄 Get Overview Details",
    tags=["📋 Overview"],
    description="""
    Get complete Overview details for a patient.
    """,
    responses={
        200: inline_serializer(
            name="OverviewDetailResponse",
            fields={
                "id": serializers.IntegerField(),
                "patient": serializers.IntegerField(),
                "clinician": serializers.IntegerField(),
                "clinician_name": serializers.CharField(),
                "patient_name": serializers.CharField(),

                # All Overview fields
                "age": serializers.IntegerField(allow_null=True),
                "living_with": serializers.CharField(),
                "living_place": serializers.CharField(),
                "occupation": serializers.CharField(),
                "occupation_history": serializers.CharField(),
                "employment_status": serializers.CharField(),
                "part_time_hours": serializers.IntegerField(allow_null=True),
                "part_time_reason": serializers.CharField(),
                "unemployment_reason": serializers.CharField(),
                "disability_payments": serializers.BooleanField(),
                "disability_reason": serializers.CharField(),
                "unable_to_work_history": serializers.BooleanField(),
                "unable_to_work_reason": serializers.CharField(),

                "presenting_problem": serializers.CharField(),
                "onset_circumstances": serializers.CharField(),
                "last_feeling_ok": serializers.CharField(),

                "first_treatment_age": serializers.CharField(),
                "first_treatment_reason": serializers.CharField(),
                "psychiatric_hospitalization": serializers.BooleanField(),
                "hospitalization_count": serializers.IntegerField(allow_null=True),
                "hospitalization_reason": serializers.CharField(),
                "substance_treatment": serializers.BooleanField(),
                "treatment_history": serializers.JSONField(),

                "physical_health": serializers.CharField(),
                "medical_hospitalization": serializers.BooleanField(),
                "medical_hospitalization_reason": serializers.CharField(),
                "current_medications": serializers.CharField(),

                "wished_dead": serializers.BooleanField(),
                "wished_dead_details": serializers.CharField(),
                "thoughts_past_week": serializers.BooleanField(),
                "strong_urge_past_week": serializers.BooleanField(),
                "strong_urge_details": serializers.CharField(),
                "intention_past_week": serializers.BooleanField(),
                "intention_details": serializers.CharField(),
                "plan_past_week": serializers.BooleanField(),
                "plan_details": serializers.CharField(),
                "suicide_attempt": serializers.BooleanField(),
                "self_harm": serializers.BooleanField(),
                "suicide_attempt_details": serializers.CharField(),
                "most_severe_attempt": serializers.CharField(),
                "attempt_past_week": serializers.BooleanField(),

                "other_problems": serializers.CharField(),
                "mood_description": serializers.CharField(),
                "alcohol_use": serializers.CharField(),
                "alcohol_with_whom": serializers.CharField(),
                "drug_use": serializers.CharField(),

                "created_at": serializers.CharField(),
                "updated_at": serializers.CharField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)


overview_update_schema = extend_schema(
    summary="✏️ Update Overview",
    tags=["📋 Overview"],
    description="""
    Update an Overview.
    
    **🔸 For PATCH (Partial Update):**
    ✅ Only send fields you want to update
    """,
    request=inline_serializer(
        name="OverviewUpdateRequest",
        fields={
            # Same as create request - all optional
            "age": serializers.IntegerField(required=False, allow_null=True),
            "living_with": serializers.CharField(required=False, allow_blank=True),
            "living_place": serializers.CharField(required=False, allow_blank=True),
            "occupation": serializers.CharField(required=False, allow_blank=True),
            "occupation_history": serializers.CharField(required=False, allow_blank=True),
            "employment_status": serializers.CharField(required=False, allow_blank=True),
            "part_time_hours": serializers.IntegerField(required=False, allow_null=True),
            "part_time_reason": serializers.CharField(required=False, allow_blank=True),
            "unemployment_reason": serializers.CharField(required=False, allow_blank=True),
            "disability_payments": serializers.BooleanField(required=False),
            "disability_reason": serializers.CharField(required=False, allow_blank=True),
            "unable_to_work_history": serializers.BooleanField(required=False),
            "unable_to_work_reason": serializers.CharField(required=False, allow_blank=True),
            "presenting_problem": serializers.CharField(required=False, allow_blank=True),
            "onset_circumstances": serializers.CharField(required=False, allow_blank=True),
            "last_feeling_ok": serializers.CharField(required=False, allow_blank=True),
            "first_treatment_age": serializers.CharField(required=False, allow_blank=True),
            "first_treatment_reason": serializers.CharField(required=False, allow_blank=True),
            "psychiatric_hospitalization": serializers.BooleanField(required=False),
            "hospitalization_count": serializers.IntegerField(required=False, allow_null=True),
            "hospitalization_reason": serializers.CharField(required=False, allow_blank=True),
            "substance_treatment": serializers.BooleanField(required=False),
            "treatment_history": serializers.JSONField(required=False),
            "physical_health": serializers.CharField(required=False, allow_blank=True),
            "medical_hospitalization": serializers.BooleanField(required=False),
            "medical_hospitalization_reason": serializers.CharField(required=False, allow_blank=True),
            "current_medications": serializers.CharField(required=False, allow_blank=True),
            "wished_dead": serializers.BooleanField(required=False),
            "wished_dead_details": serializers.CharField(required=False, allow_blank=True),
            "thoughts_past_week": serializers.BooleanField(required=False),
            "strong_urge_past_week": serializers.BooleanField(required=False),
            "strong_urge_details": serializers.CharField(required=False, allow_blank=True),
            "intention_past_week": serializers.BooleanField(required=False),
            "intention_details": serializers.CharField(required=False, allow_blank=True),
            "plan_past_week": serializers.BooleanField(required=False),
            "plan_details": serializers.CharField(required=False, allow_blank=True),
            "suicide_attempt": serializers.BooleanField(required=False),
            "self_harm": serializers.BooleanField(required=False),
            "suicide_attempt_details": serializers.CharField(required=False, allow_blank=True),
            "most_severe_attempt": serializers.CharField(required=False, allow_blank=True),
            "attempt_past_week": serializers.BooleanField(required=False),
            "other_problems": serializers.CharField(required=False, allow_blank=True),
            "mood_description": serializers.CharField(required=False, allow_blank=True),
            "alcohol_use": serializers.CharField(required=False, allow_blank=True),
            "alcohol_with_whom": serializers.CharField(required=False, allow_blank=True),
            "drug_use": serializers.CharField(required=False, allow_blank=True),
        },
    ),
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)