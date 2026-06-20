from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile to be displayed within User admin.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    extra = 0
    fieldsets = (
        (None, {
            'fields': (
                'role',
                'gender',
                'birth_date',
                'national_code',
            )
        }),
        (_('Professional Information'), {
            'fields': (
                'license_number',
                'specialization',
                'organization',
                'years_of_experience',
            )
        }),
        (_('Profile Image'), {
            'fields': ('profile_image',)
        }),
    )


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom User admin with phone number as the main identifier.
    """
    inlines = [UserProfileInline]

    list_display = (
        'phone_number',
        'full_name_display',
        'email',
        'role_display',
        'is_staff',
        'is_active',
        'created_date',
    )
    
    list_filter = (
        'is_staff',
        'is_active',
        'profile__role',
        'created_date',
    )
    
    search_fields = (
        'phone_number',
        'email',
        'first_name',
        'last_name',
        'profile__license_number'
    )
    
    ordering = ('-created_date',)
    
    # Remove created_date from fieldsets since it's auto-generated
    fieldsets = (
        (None, {
            'fields': ('phone_number', 'password')
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'email')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
        }),
        (_('Important Dates'), {
            'fields': ('last_login',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'phone_number',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'email'
            ),
        }),
    )

    # Make created_date read-only in change form
    readonly_fields = ('created_date', 'updated_date')

    def full_name_display(self, obj):
        """Display full name in list view."""
        return obj.get_full_name()
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'

    def role_display(self, obj):
        """Display user role in list view."""
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.get_role_display()
        return '-'
    role_display.short_description = 'Role'
    role_display.admin_order_field = 'profile__role'

    def get_queryset(self, request):
        """Optimize queryset with select_related for profile."""
        return super().get_queryset(request).select_related('profile')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for UserProfile model.
    """
    list_display = (
        'user_full_name',
        'phone_number_display',
        'role',
        'gender',
        'license_number',
        'specialization',
        'created_at'
    )
    
    list_filter = (
        'role',
        'gender',
        'created_at'
    )
    
    search_fields = (
        'user__phone_number',
        'user__first_name',
        'user__last_name',
        'license_number',
        'national_code'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        (_('Personal Information'), {
            'fields': (
                'birth_date',
                'gender',
                'national_code'
            )
        }),
        (_('Professional Information'), {
            'fields': (
                'role',
                'license_number',
                'specialization',
                'organization',
                'years_of_experience'
            )
        }),
        (_('Profile Image'), {
            'fields': ('profile_image',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_full_name(self, obj):
        """Display user's full name."""
        return obj.user.get_full_name()
    user_full_name.short_description = 'User'
    user_full_name.admin_order_field = 'user__first_name'

    def phone_number_display(self, obj):
        """Display user's phone number."""
        return obj.user.phone_number
    phone_number_display.short_description = 'Phone Number'
    phone_number_display.admin_order_field = 'user__phone_number'