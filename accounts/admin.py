from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from .models import User, UserProfile, Patient, PatientNote, Overview


# ============================================================
# USER PROFILE INLINE
# ============================================================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('role', 'gender', 'birth_date')
        }),
        (_('Professional Information'), {
            'fields': ('license_number', 'specialization', 'organization', 'years_of_experience')
        }),
        (_('Profile Image'), {
            'fields': ('profile_image',)
        }),
    )


# ============================================================
# USER ADMIN
# ============================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]

    list_display = (
        'phone_number',
        'full_name_display',
        'email',
        'role_display',
        'is_staff',
        'is_active',
        'patient_count',
        'overview_count',
        'created_date',
    )

    list_filter = ('is_staff', 'is_active', 'profile__role', 'created_date')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name', 'profile__license_number')
    ordering = ('-created_date',)

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important Dates'), {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'first_name', 'last_name', 'email'),
        }),
    )

    readonly_fields = ('created_date', 'updated_date')

    def full_name_display(self, obj):
        return obj.get_full_name()
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'

    def role_display(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.get_role_display()
        return '-'
    role_display.short_description = 'Role'
    role_display.admin_order_field = 'profile__role'

    def patient_count(self, obj):
        count = obj.created_patients.filter(is_active=True).count()
        if count > 0:
            url = reverse('admin:accounts_patient_changelist') + f'?created_by__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    patient_count.short_description = 'Patients'

    def overview_count(self, obj):
        count = obj.overviews.count()
        if count > 0:
            url = reverse('admin:accounts_overview_changelist') + f'?clinician__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    overview_count.short_description = 'Overviews'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')


# ============================================================
# USER PROFILE ADMIN
# ============================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'phone_number_display', 'role', 'gender', 'license_number', 'created_at')
    list_filter = ('role', 'gender', 'created_at')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name', 'license_number')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('user',)}),
        (_('Personal Information'), {'fields': ('birth_date', 'gender')}),
        (_('Professional Information'), {'fields': ('role', 'license_number', 'specialization', 'organization', 'years_of_experience')}),
        (_('Profile Image'), {'fields': ('profile_image',)}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'User'
    user_full_name.admin_order_field = 'user__first_name'

    def phone_number_display(self, obj):
        return obj.user.phone_number
    phone_number_display.short_description = 'Phone Number'
    phone_number_display.admin_order_field = 'user__phone_number'


# ============================================================
# PATIENT NOTES INLINE
# ============================================================

class PatientNoteInline(admin.TabularInline):
    model = PatientNote
    extra = 1
    fields = ('clinician', 'note_type', 'content', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    classes = ('collapse',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('clinician')


# ============================================================
# OVERVIEW INLINE
# ============================================================

class OverviewInline(admin.TabularInline):
    model = Overview
    extra = 0
    fields = ('clinician', 'age', 'occupation', 'created_at', 'view_overview_link')
    readonly_fields = ('created_at', 'view_overview_link')
    classes = ('collapse',)
    can_delete = False
    max_num = 5

    def view_overview_link(self, obj):
        if obj.id:
            url = reverse('admin:accounts_overview_change', args=[obj.id])
            return format_html('<a href="{}">View Details</a>', url)
        return '-'
    view_overview_link.short_description = 'Action'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('clinician')


# ============================================================
# PATIENT ADMIN
# ============================================================

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    inlines = [PatientNoteInline, OverviewInline]

    list_display = (
        'patient_code',
        'full_name_display',
        'phone_number',
        'gender',
        'age_display',
        'created_by_link',
        'overview_count',
        'note_count',
        'created_at',
        'is_active',
    )

    list_filter = ('gender', 'marital_status', 'education', 'is_active', 'created_at')
    search_fields = ('patient_code', 'first_name', 'last_name', 'phone_number', 'email')
    ordering = ('-created_at',)

    readonly_fields = ('patient_code', 'created_at', 'updated_at')

    fieldsets = (
        (_('Patient Information'), {'fields': ('patient_code', 'first_name', 'last_name', 'phone_number', 'email')}),
        (_('Personal Details'), {'fields': ('birth_date', 'gender', 'marital_status', 'education', 'occupation', 'address')}),
        (_('Emergency Contact'), {'fields': ('emergency_contact_name', 'emergency_contact_phone'), 'classes': ('collapse',)}),
        (_('Metadata'), {'fields': ('created_by', 'is_active', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def full_name_display(self, obj):
        return obj.get_full_name()
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'

    def age_display(self, obj):
        if obj.birth_date:
            from django.utils import timezone
            today = timezone.now().date()
            age = today.year - obj.birth_date.year - ((today.month, today.day) < (obj.birth_date.month, obj.birth_date.day))
            return f"{age} years"
        return '-'
    age_display.short_description = 'Age'

    def created_by_link(self, obj):
        if obj.created_by:
            url = reverse('admin:accounts_user_change', args=[obj.created_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.get_full_name())
        return '-'
    created_by_link.short_description = 'Created By'
    created_by_link.admin_order_field = 'created_by__first_name'

    def overview_count(self, obj):
        count = obj.overviews.count()
        if count > 0:
            url = reverse('admin:accounts_overview_changelist') + f'?patient__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    overview_count.short_description = 'Overviews'

    def note_count(self, obj):
        count = obj.notes.count()
        if count > 0:
            url = reverse('admin:accounts_patientnote_changelist') + f'?patient__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    note_count.short_description = 'Notes'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by').prefetch_related('notes', 'overviews')

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ============================================================
# PATIENT NOTE ADMIN
# ============================================================

@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_link', 'clinician_link', 'note_type', 'content_preview', 'created_at')
    list_filter = ('note_type', 'created_at', 'clinician')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__patient_code', 'content', 'clinician__first_name', 'clinician__last_name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('patient', 'clinician', 'note_type', 'content')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def patient_link(self, obj):
        if obj.patient:
            url = reverse('admin:accounts_patient_change', args=[obj.patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())
        return '-'
    patient_link.short_description = 'Patient'
    patient_link.admin_order_field = 'patient__first_name'

    def clinician_link(self, obj):
        if obj.clinician:
            url = reverse('admin:accounts_user_change', args=[obj.clinician.id])
            return format_html('<a href="{}">{}</a>', url, obj.clinician.get_full_name())
        return '-'
    clinician_link.short_description = 'Clinician'
    clinician_link.admin_order_field = 'clinician__first_name'

    def content_preview(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    content_preview.short_description = 'Content'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'clinician')


# ============================================================
# OVERVIEW ADMIN
# ============================================================

@admin.register(Overview)
class OverviewAdmin(admin.ModelAdmin):
    """
    Admin for SCID-5-CV Overview section.
    """

    list_display = (
        'id',
        'patient_link',
        'clinician_link',
        'age',
        'occupation',
        'employment_status',
        'suicide_attempt',
        'has_overview_details',
        'created_at',
    )

    list_filter = (
        'employment_status',
        'disability_payments',
        'psychiatric_hospitalization',
        'substance_treatment',
        'medical_hospitalization',
        'wished_dead',
        'suicide_attempt',
        'self_harm',
        'attempt_past_week',
        'created_at',
    )

    search_fields = (
        'patient__first_name',
        'patient__last_name',
        'patient__patient_code',
        'clinician__first_name',
        'clinician__last_name',
        'occupation',
        'presenting_problem',
    )

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('Patient & Clinician'), {
            'fields': ('patient', 'clinician')
        }),

        (_('📋 Demographic Information'), {
            'fields': (
                'age',
                'living_with',
                'living_place',
                'occupation',
                'occupation_history',
                'employment_status',
                'part_time_hours',
                'part_time_reason',
                'unemployment_reason',
                'disability_payments',
                'disability_reason',
                'unable_to_work_history',
                'unable_to_work_reason',
            )
        }),

        (_('🩺 History of Current Illness'), {
            'fields': (
                'presenting_problem',
                'onset_circumstances',
                'last_feeling_ok',
            )
        }),

        (_('💊 Treatment History'), {
            'fields': (
                'first_treatment_age',
                'first_treatment_reason',
                'psychiatric_hospitalization',
                'hospitalization_count',
                'hospitalization_reason',
                'substance_treatment',
                'treatment_history',
            )
        }),

        (_('🏥 Medical Problems'), {
            'fields': (
                'physical_health',
                'medical_hospitalization',
                'medical_hospitalization_reason',
                'current_medications',
            )
        }),

        (_('⚠️ Suicidal Ideation & Behavior'), {
            'classes': ('collapse',),
            'fields': (
                'wished_dead',
                'wished_dead_details',
                'thoughts_past_week',
                'strong_urge_past_week',
                'strong_urge_details',
                'intention_past_week',
                'intention_details',
                'plan_past_week',
                'plan_details',
                'suicide_attempt',
                'self_harm',
                'suicide_attempt_details',
                'most_severe_attempt',
                'attempt_past_week',
            )
        }),

        (_('📝 Other Current Problems'), {
            'classes': ('collapse',),
            'fields': (
                'other_problems',
                'mood_description',
                'alcohol_use',
                'alcohol_with_whom',
                'drug_use',
            )
        }),

        (_('📅 Metadata'), {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def patient_link(self, obj):
        if obj.patient:
            url = reverse('admin:accounts_patient_change', args=[obj.patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())
        return '-'
    patient_link.short_description = 'Patient'
    patient_link.admin_order_field = 'patient__first_name'

    def clinician_link(self, obj):
        if obj.clinician:
            url = reverse('admin:accounts_user_change', args=[obj.clinician.id])
            return format_html('<a href="{}">{}</a>', url, obj.clinician.get_full_name())
        return '-'
    clinician_link.short_description = 'Clinician'
    clinician_link.admin_order_field = 'clinician__first_name'

    def has_overview_details(self, obj):
        """Check if overview has any meaningful content."""
        fields_to_check = [
            obj.age, obj.occupation, obj.presenting_problem,
            obj.physical_health, obj.wished_dead, obj.suicide_attempt
        ]
        if any(fields_to_check):
            return True
        return False
    has_overview_details.boolean = True
    has_overview_details.short_description = 'Has Data'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'clinician')

    def save_model(self, request, obj, form, change):
        if not change and not obj.clinician:
            obj.clinician = request.user
        super().save_model(request, obj, form, change)