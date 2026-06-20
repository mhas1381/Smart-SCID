"""
API v1 serializers for accounts app.
"""

from typing import Optional, Dict, Any
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password as django_validate_password
from drf_spectacular.utils import extend_schema_field
from ...models import User, UserProfile, Patient, PatientNote, Overview
import re
import logging

logger = logging.getLogger("accounts")
User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that returns user info along with tokens.
    """

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        data = super().validate(attrs)
        user = self.user

        try:
            profile = user.profile
            data["user"] = {
                "id": user.id,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": profile.role,
                "profile_image": profile.profile_image.url if profile.profile_image else None,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "has_password": user.has_usable_password(),
            }
        except UserProfile.DoesNotExist:
            data["user"] = {
                "id": user.id,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": "clinician",
                "profile_image": None,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "has_password": user.has_usable_password(),
            }

        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with phone number and password.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        error_messages={
            "required": "وارد کردن رمز عبور الزامی است.",
            "blank": "رمز عبور نمی‌تواند خالی باشد.",
            "min_length": "رمز عبور باید حداقل ۸ کاراکتر باشد.",
        },
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            "required": "وارد کردن تکرار رمز عبور الزامی است.",
            "blank": "تکرار رمز عبور نمی‌تواند خالی باشد.",
        },
    )

    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
    )

    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            'phone_number',
            'password',
            'confirm_password',
            'first_name',
            'last_name',
            'email',
        ]

    def validate_phone_number(self, value: str) -> str:
        phone_regex = re.compile(r"^09\d{9}$")
        if not phone_regex.match(value):
            raise serializers.ValidationError(
                "شماره تلفن همراه باید با 09 شروع شود و ۱۱ رقم باشد."
            )

        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "کاربری با این شماره تلفن قبلاً ثبت نام کرده است."
            )

        return value

    def validate_password(self, value: str) -> str:
        if len(value) < 8:
            raise serializers.ValidationError("رمز عبور باید حداقل ۸ کاراکتر باشد.")

        if not re.search(r"\d", value):
            raise serializers.ValidationError("رمز عبور باید حداقل شامل یک عدد باشد.")

        if not re.search(r"[a-zA-Z]", value):
            raise serializers.ValidationError(
                "رمز عبور باید حداقل شامل یک حرف انگلیسی باشد."
            )

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', value):
            raise serializers.ValidationError(
                "رمز عبور باید حداقل شامل یک کاراکتر خاص باشد."
            )

        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "رمز عبور و تکرار آن یکسان نیستند."}
            )

        return attrs

    def create(self, validated_data: Dict[str, Any]) -> User:
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            phone_number=validated_data.get("phone_number"),
            password=password,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data.get("email", ""),
        )

        return user


class SendOTPSerializer(serializers.Serializer):
    """
    Serializer for sending OTP to phone number.
    """

    phone_number = serializers.CharField(
        max_length=11,
        min_length=11,
        required=True,
        error_messages={
            "required": "وارد کردن شماره تلفن الزامی است.",
            "blank": "شماره تلفن نمی‌تواند خالی باشد.",
            "min_length": "شماره تلفن باید دقیقاً ۱۱ رقم باشد.",
            "max_length": "شماره تلفن باید دقیقاً ۱۱ رقم باشد.",
        },
    )

    def validate_phone_number(self, value: str) -> str:
        phone_regex = re.compile(r"^09\d{9}$")
        if not phone_regex.match(value):
            raise serializers.ValidationError(
                "شماره تلفن همراه باید با 09 شروع شود و ۱۱ رقم باشد."
            )
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for verifying OTP and authenticating user.
    """

    phone_number = serializers.CharField(
        max_length=11,
        min_length=11,
        required=True,
        error_messages={
            "required": "وارد کردن شماره تلفن الزامی است.",
            "blank": "شماره تلفن نمی‌تواند خالی باشد.",
            "min_length": "شماره تلفن باید دقیقاً ۱۱ رقم باشد.",
            "max_length": "شماره تلفن باید دقیقاً ۱۱ رقم باشد.",
        },
    )

    otp_code = serializers.CharField(
        max_length=5,
        min_length=5,
        required=True,
        error_messages={
            "required": "وارد کردن کد تایید الزامی است.",
            "blank": "کد تایید نمی‌تواند خالی باشد.",
            "min_length": "کد تایید باید دقیقاً ۵ رقم باشد.",
            "max_length": "کد تایید باید دقیقاً ۵ رقم باشد.",
        },
    )


class SetPasswordSerializer(serializers.Serializer):
    """
    Serializer for setting/creating user password.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        error_messages={
            "required": "وارد کردن رمز عبور الزامی است.",
            "blank": "رمز عبور نمی‌تواند خالی باشد.",
            "min_length": "رمز عبور باید حداقل ۸ کاراکتر باشد.",
        },
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            "required": "وارد کردن تکرار رمز عبور الزامی است.",
            "blank": "تکرار رمز عبور نمی‌تواند خالی باشد.",
        },
    )

    def validate_password(self, value: str) -> str:
        if len(value) < 8:
            raise serializers.ValidationError("رمز عبور باید حداقل ۸ کاراکتر باشد.")

        if not re.search(r"\d", value):
            raise serializers.ValidationError("رمز عبور باید حداقل شامل یک عدد باشد.")

        if not re.search(r"[a-zA-Z]", value):
            raise serializers.ValidationError(
                "رمز عبور باید حداقل شامل یک حرف انگلیسی باشد."
            )

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', value):
            raise serializers.ValidationError(
                "رمز عبور باید حداقل شامل یک کاراکتر خاص باشد."
            )

        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "رمز عبور و تکرار آن یکسان نیستند."}
            )

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model.
    """

    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user',
            'full_name',
            'phone_number',
            'birth_date',
            'gender',
            'national_code',
            'role',
            'license_number',
            'specialization',
            'organization',
            'years_of_experience',
            'profile_image',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField)
    def get_full_name(self, obj: UserProfile) -> str:
        return obj.full_name

    @extend_schema_field(serializers.CharField)
    def get_phone_number(self, obj: UserProfile) -> str:
        return obj.phone_number


class UserMeSerializer(serializers.Serializer):
    """
    Serializer for authenticated user's profile.
    """

    id = serializers.IntegerField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    has_password = serializers.BooleanField(read_only=True)

    @extend_schema_field(serializers.CharField)
    def get_role(self, obj: User) -> str:
        try:
            return obj.profile.role
        except UserProfile.DoesNotExist:
            return "clinician"

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_image(self, obj: User) -> Optional[str]:
        try:
            if obj.profile.profile_image:
                return obj.profile.profile_image.url
        except UserProfile.DoesNotExist:
            pass
        return None


class PatientListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing patients (brief information).
    """

    full_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_code',
            'full_name',
            'phone_number',
            'gender',
            'birth_date',
            'created_by_name',
            'created_at',
            'is_active',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name()


class PatientDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for patient detail (full information).
    """

    created_by_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_code',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'email',
            'national_code',
            'birth_date',
            'age',
            'gender',
            'marital_status',
            'education',
            'occupation',
            'address',
            'emergency_contact_name',
            'emergency_contact_phone',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'is_active',
        ]
        read_only_fields = [
            'id',
            'patient_code',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
            'full_name',
            'age',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name()

    def get_age(self, obj):
        if obj.birth_date:
            from django.utils import timezone
            today = timezone.now().date()
            return today.year - obj.birth_date.year - (
                (today.month, today.day) < (obj.birth_date.month, obj.birth_date.day)
            )
        return None


class PatientCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new patient.
    """

    class Meta:
        model = Patient
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'email',
            'national_code',
            'birth_date',
            'gender',
            'marital_status',
            'education',
            'occupation',
            'address',
            'emergency_contact_name',
            'emergency_contact_phone',
        ]
        # Add read-only fields for patient_code and id
        read_only_fields = ['patient_code', 'id']

    def validate_phone_number(self, value):
        if value:
            phone_regex = re.compile(r"^09\d{9}$")
            if not phone_regex.match(value):
                raise serializers.ValidationError(
                    "شماره تلفن همراه باید با 09 شروع شود و ۱۱ رقم باشد."
                )
        return value

    def validate_national_code(self, value):
        # Skip validation if empty or None (it's optional)
        if not value:
            return value
            
        if not re.match(r"^\d{10}$", value):
            raise serializers.ValidationError("کد ملی باید دقیقاً ۱۰ رقم باشد.")

        check = int(value[9])
        s = sum(int(value[x]) * (10 - x) for x in range(9)) % 11
        if (s < 2 and check != s) or (s >= 2 and check + s != 11):
            raise serializers.ValidationError("کد ملی نامعتبر است.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("User must be authenticated.")

        validated_data['created_by'] = request.user
        patient = Patient.objects.create(**validated_data)
        return patient

class PatientUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a patient.
    """

    class Meta:
        model = Patient
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'email',
            'national_code',
            'birth_date',
            'gender',
            'marital_status',
            'education',
            'occupation',
            'address',
            'emergency_contact_name',
            'emergency_contact_phone',
            'is_active',
        ]

    def validate_phone_number(self, value):
        if value:
            phone_regex = re.compile(r"^09\d{9}$")
            if not phone_regex.match(value):
                raise serializers.ValidationError(
                    "شماره تلفن همراه باید با 09 شروع شود و ۱۱ رقم باشد."
                )
        return value

    def validate_national_code(self, value):
        if value:
            if not re.match(r"^\d{10}$", value):
                raise serializers.ValidationError("کد ملی باید دقیقاً ۱۰ رقم باشد.")

            check = int(value[9])
            s = sum(int(value[x]) * (10 - x) for x in range(9)) % 11
            if (s < 2 and check != s) or (s >= 2 and check + s != 11):
                raise serializers.ValidationError("کد ملی نامعتبر است.")
        return value


class PatientNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for patient notes.
    """

    clinician_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientNote
        fields = [
            'id',
            'patient',
            'clinician',
            'clinician_name',
            'note_type',
            'content',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'clinician', 'clinician_name', 'created_at', 'updated_at']
        extra_kwargs = {
            'patient': {'required': False},
        }

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()


class OverviewSerializer(serializers.ModelSerializer):
    """
    Serializer for SCID-5-CV Overview section.
    """

    clinician_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    message = serializers.CharField(read_only=True, default="Overview created successfully")

    class Meta:
        model = Overview
        fields = [
            'id', 'patient', 'clinician', 'clinician_name', 'patient_name', 'message',
            'age', 'living_with', 'living_place', 'occupation', 'occupation_history',
            'employment_status', 'part_time_hours', 'part_time_reason', 'unemployment_reason',
            'disability_payments', 'disability_reason', 'unable_to_work_history',
            'unable_to_work_reason',
            'presenting_problem', 'onset_circumstances', 'last_feeling_ok',
            'first_treatment_age', 'first_treatment_reason', 'psychiatric_hospitalization',
            'hospitalization_count', 'hospitalization_reason', 'substance_treatment',
            'treatment_history', 'physical_health', 'medical_hospitalization',
            'medical_hospitalization_reason', 'current_medications',
            'wished_dead', 'wished_dead_details', 'thoughts_past_week',
            'strong_urge_past_week', 'strong_urge_details', 'intention_past_week',
            'intention_details', 'plan_past_week', 'plan_details',
            'suicide_attempt', 'self_harm', 'suicide_attempt_details',
            'most_severe_attempt', 'attempt_past_week',
            'other_problems', 'mood_description', 'alcohol_use',
            'alcohol_with_whom', 'drug_use',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'clinician', 'created_at', 'updated_at', 'message']
        extra_kwargs = {
            'patient': {'required': False},
        }

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()


class OverviewListSerializer(serializers.ModelSerializer):
    """
    Brief serializer for listing Overviews.
    """

    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()

    class Meta:
        model = Overview
        fields = [
            'id',
            'patient',
            'patient_name',
            'clinician',
            'clinician_name',
            'age',
            'occupation',
            'suicide_attempt',
            'created_at',
        ]

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()