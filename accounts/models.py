from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
)
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
import re


class UserManager(BaseUserManager):
    """
    Custom user manager using phone number as the main identifier.
    """

    def create_user(self, phone_number, password=None, **extra_fields):
        """
        Create and save a User with the given phone number and password.
        """
        if not phone_number:
            raise ValueError(_("The Phone Number must be set."))

        if extra_fields.get("email"):
            extra_fields["email"] = self.normalize_email(extra_fields["email"])

        user = self.model(phone_number=phone_number, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given phone number and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model where phone number is the primary identifier.
    """

    # Phone number validator for Iranian format (e.g., 09123456789)
    phone_regex = RegexValidator(
        regex=r"^09\d{9}$",
        message=_("Phone number must be entered in the format: '09123456789'."),
    )

    phone_number = models.CharField(
        max_length=11,
        unique=True,
        validators=[phone_regex],
        verbose_name=_("Phone Number"),
        help_text=_("Required. 11 digits format: 09xxxxxxxxx"),
        error_messages={
            "unique": _("A user with this phone number already exists."),
        },
    )

    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Email Address"),
    )

    first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("First Name"),
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Last Name"),
    )

    # Django internal fields
    is_superuser = models.BooleanField(
        default=False,
        verbose_name=_("Superuser Status"),
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_("Staff Status"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Verified"),
        help_text=_("Designates whether the user's phone number is verified."),
    )

    # Fix reverse accessor clash - add unique related_name
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        verbose_name=_('groups'),
        help_text=_('The groups this user belongs to.'),
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        verbose_name=_('user permissions'),
        help_text=_('Specific permissions for this user.'),
    )

    # Timestamps
    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created Date"),
    )
    updated_date = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated Date"),
    )

    # Custom manager
    objects = UserManager()

    # Field used for authentication
    USERNAME_FIELD = "phone_number"

    # Fields required when creating a superuser
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_date"]

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.phone_number})"
        return self.phone_number

    def get_full_name(self):
        """Return the full name of the user."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.phone_number

    def get_short_name(self):
        """Return the short name of the user."""
        if self.first_name:
            return self.first_name
        return self.phone_number


class UserProfile(models.Model):
    """
    Model to store additional user profile data.
    """

    GENDER_CHOICES = [
        ("male", _("Male")),
        ("female", _("Female")),
        ("other", _("Other")),
    ]

    ROLE_CHOICES = [
        ("admin", _("Administrator")),
        ("clinician", _("Clinician")),
        ("researcher", _("Researcher")),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
        help_text=_("The user this profile belongs to."),
    )

    # Personal Information
    birth_date = models.DateField(
        verbose_name=_("Birth Date"),
        null=True,
        blank=True,
    )

    gender = models.CharField(
        verbose_name=_("Gender"),
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
    )

    national_code = models.CharField(
        verbose_name=_("National Code"),
        max_length=10,
        null=True,
        blank=True,
    )

    # Professional Information
    role = models.CharField(
        verbose_name=_("User Role"),
        max_length=20,
        choices=ROLE_CHOICES,
        default="clinician",
        help_text=_("The user's role in the system."),
    )

    license_number = models.CharField(
        verbose_name=_("License Number"),
        max_length=50,
        blank=True,
        help_text=_("Professional license number for clinicians."),
    )

    specialization = models.CharField(
        verbose_name=_("Specialization"),
        max_length=200,
        blank=True,
        help_text=_("Clinical specialization (e.g., Clinical Psychology, Psychiatry)."),
    )

    organization = models.CharField(
        verbose_name=_("Organization"),
        max_length=200,
        blank=True,
        help_text=_("Workplace or organization name."),
    )

    years_of_experience = models.PositiveIntegerField(
        verbose_name=_("Years of Experience"),
        null=True,
        blank=True,
    )

    profile_image = models.ImageField(
        verbose_name=_("Profile Image"),
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    # Timestamps
    created_at = models.DateTimeField(
        verbose_name=_("Created At"),
        auto_now_add=True,
        editable=False,
    )
    updated_at = models.DateTimeField(
        verbose_name=_("Updated At"),
        auto_now=True,
        editable=False,
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        ordering = ["user__created_date"]

    def __str__(self):
        return f"Profile of {self.user.get_full_name()}"

    def clean(self):
        """Validate profile data."""
        if self.national_code:
            # Check length
            if not re.match(r"^\d{10}$", self.national_code):
                raise ValidationError(_("National code must be exactly 10 digits."))
            
            # Iranian National Code checksum algorithm
            check = int(self.national_code[9])
            s = sum(int(self.national_code[x]) * (10 - x) for x in range(9)) % 11
            if (s < 2 and check != s) or (s >= 2 and check + s != 11):
                raise ValidationError(_("National code is invalid."))

    def save(self, *args, **kwargs):
        """Override save to delete old profile image when updated."""
        if self.pk:
            try:
                old_instance = UserProfile.objects.get(pk=self.pk)
                if old_instance.profile_image and old_instance.profile_image != self.profile_image:
                    old_instance.profile_image.delete(save=False)
            except UserProfile.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return the user's full name."""
        return self.user.get_full_name()

    @property
    def phone_number(self):
        """Return the user's phone number."""
        return self.user.phone_number


# ============================================================
# SIGNALS: Auto-create profile when user is created
# ============================================================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created.
    """
    if created:
        try:
            UserProfile.objects.create(user=instance)
        except Exception as e:
            print(f"Error creating profile for {instance.phone_number}: {e}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save profile when user is saved.
    """
    if hasattr(instance, "profile"):
        try:
            instance.profile.save()
        except Exception:
            pass