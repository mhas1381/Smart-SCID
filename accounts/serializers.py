from rest_framework import serializers
from accounts.models import Patient, User, UserProfile
from django.core.exceptions import ValidationError
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with user profile data"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name',
            'full_name', 'is_verified', 'is_active', 'is_staff', 'is_superuser',
            'created_date', 'updated_date', 'age'
        ]
        read_only_fields = [
            'id', 'is_verified', 'is_active', 'is_staff',
            'is_superuser', 'created_date', 'updated_date'
        ]

    def get_age(self, obj):
        """Calculate user age from profile"""
        if hasattr(obj, 'profile') and obj.profile.birth_date:
            today = timezone.now().date()
            return today.year - obj.profile.birth_date.year - (
                (today.month, today.day) < (obj.profile.birth_date.month, obj.profile.birth_date.day)
            )
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'full_name', 'phone_number', 'birth_date', 'gender',
            'role', 'license_number', 'specialization', 'organization',
            'years_of_experience', 'profile_image', 'age', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_age(self, obj):
        """Calculate user age"""
        if obj.birth_date:
            today = timezone.now().date()
            return today.year - obj.birth_date.year - (
                (today.month, today.day) < (obj.birth_date.month, obj.birth_date.day)
            )
        return None


class PatientListSerializer(serializers.ModelSerializer):
    """Serializer for listing patients with basic information"""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'patient_code', 'first_name', 'last_name', 'full_name',
            'phone_number', 'email', 'age', 'gender', 'created_by',
            'created_by_name', 'created_at', 'is_active'
        ]
        read_only_fields = ['id', 'patient_code', 'created_by', 'created_at']

    def get_age(self, obj):
        """Calculate patient age"""
        return obj.get_age()


class PatientDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed patient information"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'patient_code', 'first_name', 'last_name', 'full_name',
            'phone_number', 'email', 'birth_date', 'age', 'gender', 
            'marital_status', 'education', 'occupation', 'address',
            'emergency_contact_name', 'emergency_contact_phone', 
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'is_active'
        ]
        read_only_fields = ['id', 'patient_code', 'created_by', 'created_at', 'updated_at']

    def get_age(self, obj):
        """Calculate patient age"""
        return obj.get_age()

    def validate_birth_date(self, value):
        """Validate birth date is not in the future"""
        if value and value > timezone.now().date():
            raise ValidationError("Birth date cannot be in the future")
        return value

    def validate_phone_number(self, value):
        """Validate phone number format if provided"""
        if value:
            from django.core.validators import RegexValidator
            phone_validator = RegexValidator(
                regex=r"^09\d{9}$",
                message="Phone number must be in format: 09123456789"
            )
            phone_validator(value)
        return value

    def validate_emergency_contact_phone(self, value):
        """Validate emergency contact phone format if provided"""
        if value:
            from django.core.validators import RegexValidator
            phone_validator = RegexValidator(
                regex=r"^09\d{9}$",
                message="Emergency contact phone must be in format: 09123456789"
            )
            phone_validator(value)
        return value


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new patients"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'full_name', 'phone_number', 
            'email', 'birth_date', 'gender', 'marital_status', 
            'education', 'occupation', 'address',
            'emergency_contact_name', 'emergency_contact_phone'
        ]

    def validate_birth_date(self, value):
        """Validate birth date is not in the future"""
        if value and value > timezone.now().date():
            raise ValidationError("Birth date cannot be in the future")
        return value

    def validate_phone_number(self, value):
        """Validate phone number format if provided"""
        if value:
            from django.core.validators import RegexValidator
            phone_validator = RegexValidator(
                regex=r"^09\d{9}$",
                message="Phone number must be in format: 09123456789"
            )
            phone_validator(value)
        return value

    def validate_emergency_contact_phone(self, value):
        """Validate emergency contact phone format if provided"""
        if value:
            from django.core.validators import RegexValidator
            phone_validator = RegexValidator(
                regex=r"^09\d{9}$",
                message="Emergency contact phone must be in format: 09123456789"
            )
            phone_validator(value)
        return value

    def create(self, validated_data):
        """Set created_by from context"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)