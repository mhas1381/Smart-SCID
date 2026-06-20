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
from django.db import models
from django.core.cache import cache
from drf_spectacular.utils import extend_schema_view
from django.shortcuts import get_object_or_404
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
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateSerializer,
    PatientUpdateSerializer,
    PatientNoteSerializer,
    OverviewSerializer,
    OverviewListSerializer,
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
    patient_list_schema,
    patient_create_schema,
    patient_detail_schema,
    patient_update_schema,
    patient_delete_schema,
    patient_note_list_schema,
    patient_note_create_schema,
    overview_create_schema,
    overview_detail_schema,
    overview_list_schema,
    overview_update_schema,
    overview_questions_schema,
)
from ...models import UserProfile, Patient, PatientNote, Overview
from utils.sms import send_verification_code

User = get_user_model()
logger = logging.getLogger("accounts")

OTP_LENGTH = 5
CACHE_TIMEOUT = 120


# ============================================================
# 🔐 AUTHENTICATION VIEWS
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
# 👤 USER PROFILE VIEWS
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


# ============================================================
# 👤 PATIENT VIEWS
# ============================================================

@extend_schema_view(
    get=patient_list_schema,
    post=patient_create_schema,
)
class PatientListCreateView(generics.ListCreateAPIView):
    """
    List all patients or create a new patient.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PatientCreateSerializer
        return PatientListSerializer

    def get_queryset(self):
        return Patient.objects.filter(created_by=self.request.user, is_active=True)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            patient = serializer.save()
            response_serializer = PatientDetailSerializer(patient, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=patient_detail_schema,
    put=patient_update_schema,
    patch=patient_update_schema,
    delete=patient_delete_schema,
)
class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a patient.
    """
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'pk'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PatientUpdateSerializer
        return PatientDetailSerializer

    def get_queryset(self):
        return Patient.objects.filter(created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


# ============================================================
# 📝 PATIENT NOTE VIEWS
# ============================================================

@extend_schema_view(
    get=patient_note_list_schema,
    post=patient_note_create_schema,
)
class PatientNoteListCreateView(generics.ListCreateAPIView):
    """
    List notes for a patient or add a new note.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PatientNoteSerializer

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id, created_by=self.request.user)
        return PatientNote.objects.filter(patient=patient)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def perform_create(self, serializer):
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id, created_by=self.request.user)
        serializer.save(patient=patient, clinician=self.request.user)


# ============================================================
# 📋 OVERVIEW VIEWS
# ============================================================
@extend_schema_view(
    get=overview_questions_schema,
)
class OverviewQuestionsView(APIView):
    """
    Get all Overview questions with their metadata.
    Questions are extracted from model field help_text.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        questions = self._get_questions()
        return Response({
            'sections': self._group_by_sections(questions),
            'total': len(questions)
        })

    def _get_questions(self):
        """Extract questions from model fields"""
        questions = []
        
        # Fields to exclude (metadata fields)
        exclude_fields = ['id', 'patient', 'clinician', 'created_at', 'updated_at']
        
        for field in Overview._meta.get_fields():
            if field.name in exclude_fields:
                continue
            
            # Skip reverse relations
            if field.auto_created:
                continue
            
            question = self._parse_field(field)
            if question:
                questions.append(question)
        
        return questions

    def _parse_field(self, field):
        """Parse a single field into a question object"""
        from django.db.models.fields import NOT_PROVIDED
        
        question = {
            'id': field.name,
            'type': self._get_field_type(field),
            'text': field.help_text or field.verbose_name or field.name,
            'required': not field.blank,
            'section': self._get_section(field.name),
        }
        
        # Add choices if field has choices
        if hasattr(field, 'choices') and field.choices:
            question['choices'] = [
                {'value': choice[0], 'label': choice[1]} 
                for choice in field.choices
            ]
        
        # Add default value - check for NOT_PROVIDED
        if hasattr(field, 'default') and field.default is not NOT_PROVIDED:
            default_value = field.default
            # If default is a callable, call it to get the actual value
            if callable(default_value):
                try:
                    default_value = default_value()
                except Exception:
                    default_value = None
            # If default is a type (like bool, str, int), convert to appropriate value
            elif isinstance(default_value, type):
                if default_value is bool:
                    default_value = False
                elif default_value is str:
                    default_value = ""
                elif default_value is int:
                    default_value = 0
                elif default_value is list:
                    default_value = []
                elif default_value is dict:
                    default_value = {}
                else:
                    default_value = None
            question['default'] = default_value
        
        return question

    def _get_field_type(self, field):
        """Determine field type for frontend rendering"""
        if isinstance(field, models.BooleanField):
            return 'boolean'
        if isinstance(field, models.TextField):
            return 'textarea'
        if isinstance(field, models.CharField) and hasattr(field, 'choices') and field.choices:
            return 'select'
        if isinstance(field, models.CharField):
            return 'text'
        if isinstance(field, models.IntegerField) or isinstance(field, models.PositiveIntegerField):
            return 'number'
        if isinstance(field, models.DateField):
            return 'date'
        if isinstance(field, models.JSONField):
            return 'json'
        return 'text'

    def _get_section(self, field_name):
        """Group fields by logical sections"""
        demographic = [
            'living_with', 'living_place', 'occupation_history',
            'employment_status', 'part_time_hours', 'part_time_reason',
            'unemployment_reason', 'disability_payments', 'disability_reason',
            'unable_to_work_history', 'unable_to_work_reason'
        ]
        illness_history = [
            'presenting_problem', 'onset_circumstances', 'last_feeling_ok'
        ]
        treatment_history = [
            'first_treatment_age', 'first_treatment_reason',
            'psychiatric_hospitalization', 'hospitalization_count',
            'hospitalization_reason', 'substance_treatment', 'treatment_history'
        ]
        medical = [
            'physical_health', 'medical_hospitalization',
            'medical_hospitalization_reason', 'current_medications'
        ]
        suicidal = [
            'wished_dead', 'wished_dead_details', 'thoughts_past_week',
            'strong_urge_past_week', 'strong_urge_details',
            'intention_past_week', 'intention_details',
            'plan_past_week', 'plan_details',
            'suicide_attempt', 'self_harm', 'suicide_attempt_details',
            'most_severe_attempt', 'attempt_past_week'
        ]
        other = [
            'other_problems', 'mood_description', 'alcohol_use',
            'alcohol_with_whom', 'drug_use'
        ]
        
        if field_name in demographic:
            return 'demographic'
        elif field_name in illness_history:
            return 'illness_history'
        elif field_name in treatment_history:
            return 'treatment_history'
        elif field_name in medical:
            return 'medical'
        elif field_name in suicidal:
            return 'suicidal'
        elif field_name in other:
            return 'other'
        return 'other'

    def _group_by_sections(self, questions):
        """Group questions by section"""
        sections_map = {}
        
        for q in questions:
            section_key = q.pop('section')
            if section_key not in sections_map:
                sections_map[section_key] = {
                    'id': section_key,
                    'title': self._get_section_title(section_key),
                    'icon': self._get_section_icon(section_key),
                    'questions': []
                }
            sections_map[section_key]['questions'].append(q)
        
        return list(sections_map.values())

    def _get_section_title(self, section_key):
        titles = {
            'demographic': 'Demographic Information',
            'illness_history': 'History of Current Illness',
            'treatment_history': 'Treatment History',
            'medical': 'Medical Problems',
            'suicidal': 'Suicidal Ideation & Behavior',
            'other': 'Other Current Problems'
        }
        return titles.get(section_key, section_key)

    def _get_section_icon(self, section_key):
        icons = {
            'demographic': '👤',
            'illness_history': '🩺',
            'treatment_history': '💊',
            'medical': '🏥',
            'suicidal': '⚠️',
            'other': '📝'
        }
        return icons.get(section_key, '📋')
    
@extend_schema_view(
    get=overview_list_schema,
    post=overview_create_schema,
)
class OverviewListCreateView(generics.ListCreateAPIView):
    """
    List all overviews for a patient or create a new overview.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OverviewSerializer
        return OverviewListSerializer

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id, created_by=self.request.user)
        return Overview.objects.filter(patient=patient)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def perform_create(self, serializer):
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id, created_by=self.request.user)
        serializer.save(patient=patient, clinician=self.request.user)


@extend_schema_view(
    get=overview_detail_schema,
    put=overview_update_schema,
    patch=overview_update_schema,
)
class OverviewDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update an overview.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OverviewSerializer
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        return Overview.objects.filter(patient__created_by=self.request.user)
    
    
