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


# ============================================================
# USER MANAGER
# ============================================================

class UserManager(BaseUserManager):
    """
    Custom user manager using phone number as the main identifier.
    """

    def create_user(self, phone_number, password=None, **extra_fields):
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
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(phone_number, password, **extra_fields)


# ============================================================
# USER MODEL
# ============================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model where phone number is the primary identifier.
    """

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

    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created Date"),
    )
    updated_date = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated Date"),
    )

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
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
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.phone_number

    def get_short_name(self):
        if self.first_name:
            return self.first_name
        return self.phone_number


# ============================================================
# USER PROFILE MODEL
# ============================================================

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
        help_text=_("Clinical specialization."),
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

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        ordering = ["user__created_date"]

    def __str__(self):
        return f"Profile of {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
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
        return self.user.get_full_name()

    @property
    def phone_number(self):
        return self.user.phone_number


# ============================================================
# PATIENT MODEL
# ============================================================

class Patient(models.Model):
    """
    Patient model for SCID-5 interviews.
    Patients do NOT have user accounts - they are managed by clinicians.
    """

    GENDER_CHOICES = [
        ("male", _("Male")),
        ("female", _("Female")),
        ("other", _("Other")),
    ]

    MARITAL_STATUS_CHOICES = [
        ("single", _("Single")),
        ("married", _("Married")),
        ("divorced", _("Divorced")),
        ("widowed", _("Widowed")),
    ]

    EDUCATION_CHOICES = [
        ("elementary", _("Elementary")),
        ("middle_school", _("Middle School")),
        ("high_school", _("High School")),
        ("diploma", _("Diploma")),
        ("associate", _("Associate Degree")),
        ("bachelor", _("Bachelor's Degree")),
        ("master", _("Master's Degree")),
        ("doctoral", _("Doctoral Degree")),
    ]

    # ===== Patient Identifier =====
    patient_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name=_("Patient Code"),
        help_text=_("Unique code generated automatically for each patient."),
    )

    # ===== Personal Information =====
    first_name = models.CharField(
        max_length=150,
        verbose_name=_("First Name"),
    )

    last_name = models.CharField(
        max_length=150,
        verbose_name=_("Last Name"),
    )

    phone_regex = RegexValidator(
        regex=r"^09\d{9}$",
        message=_("Phone number must be entered in the format: '09123456789'."),
    )

    phone_number = models.CharField(
        max_length=11,
        validators=[phone_regex],
        verbose_name=_("Phone Number"),
        blank=True,
    )

    email = models.EmailField(
        verbose_name=_("Email Address"),
        blank=True,
    )

    birth_date = models.DateField(
        verbose_name=_("Birth Date"),
        null=True,
        blank=True,
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        verbose_name=_("Gender"),
        null=True,
        blank=True,
    )

    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        verbose_name=_("Marital Status"),
        null=True,
        blank=True,
    )

    education = models.CharField(
        max_length=20,
        choices=EDUCATION_CHOICES,
        verbose_name=_("Education Level"),
        null=True,
        blank=True,
    )

    occupation = models.CharField(
        max_length=200,
        verbose_name=_("Occupation"),
        blank=True,
    )

    address = models.TextField(
        verbose_name=_("Address"),
        blank=True,
    )

    # ===== Emergency Contact =====
    emergency_contact_name = models.CharField(
        max_length=150,
        verbose_name=_("Emergency Contact Name"),
        blank=True,
    )

    emergency_contact_phone = models.CharField(
        max_length=11,
        validators=[phone_regex],
        verbose_name=_("Emergency Contact Phone"),
        blank=True,
    )

    # ===== Metadata =====
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_patients",
        verbose_name=_("Created By"),
        help_text=_("The clinician who created this patient record."),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Inactive patients are hidden from lists."),
    )

    class Meta:
        verbose_name = _("Patient")
        verbose_name_plural = _("Patients")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_code})"

    def save(self, *args, **kwargs):
        if not self.patient_code:
            self.patient_code = self._generate_patient_code()
        super().save(*args, **kwargs)

    def _generate_patient_code(self) -> str:
        from django.utils import timezone
        import uuid
        timestamp = timezone.now().strftime("%Y%m")
        short_uuid = str(uuid.uuid4()).replace("-", "").upper()[:6]
        return f"P-{timestamp}-{short_uuid}"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_age(self):
        if self.birth_date:
            from django.utils import timezone
            today = timezone.now().date()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None


# ============================================================
# OVERVIEW MODEL (SCID-5-CV Overview Section)
# ============================================================

class Overview(models.Model):
    """
    SCID-5-CV Overview section.
    Contains ONLY information that is NOT already in Patient model.
    """

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="overviews",
        verbose_name=_("Patient"),
    )

    clinician = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="overviews",
        verbose_name=_("Clinician"),
    )

    # ==========================================================
    # DEMOGRAPHIC INFORMATION (Complementary to Patient)
    # ==========================================================

    living_with = models.CharField(
        max_length=200,
        verbose_name=_("Living With"),
        blank=True,
        help_text=_("With whom do you live?"),
    )

    living_place = models.CharField(
        max_length=200,
        verbose_name=_("Living Place"),
        blank=True,
        help_text=_("What kind of place do you live in?"),
    )

    occupation_history = models.CharField(
        max_length=200,
        verbose_name=_("Occupation History"),
        blank=True,
        help_text=_("Have you always done that kind of work?"),
    )

    employment_status = models.CharField(
        max_length=50,
        verbose_name=_("Employment Status"),
        blank=True,
        help_text=_("Are you currently employed (getting paid)?"),
    )

    part_time_hours = models.PositiveIntegerField(
        verbose_name=_("Part-time Hours"),
        blank=True,
        null=True,
        help_text=_("How many hours do you typically work each week?"),
    )

    part_time_reason = models.TextField(
        verbose_name=_("Part-time Reason"),
        blank=True,
        help_text=_("Why do you work part-time instead of full-time?"),
    )

    unemployment_reason = models.TextField(
        verbose_name=_("Unemployment Reason"),
        blank=True,
        help_text=_("Why is that? When was the last time you worked? How are you supporting yourself now?"),
    )

    disability_payments = models.BooleanField(
        default=False,
        verbose_name=_("Disability Payments"),
        help_text=_("Are you currently receiving disability payments?"),
    )

    disability_reason = models.TextField(
        verbose_name=_("Disability Reason"),
        blank=True,
        help_text=_("Why are you on disability?"),
    )

    unable_to_work_history = models.BooleanField(
        default=False,
        verbose_name=_("Unable to Work History"),
        help_text=_("Has there ever been a period of time when you were unable to work or go to school?"),
    )

    unable_to_work_reason = models.TextField(
        verbose_name=_("Unable to Work Reason"),
        blank=True,
        help_text=_("Why was that?"),
    )

    # ==========================================================
    # HISTORY OF CURRENT ILLNESS
    # ==========================================================

    presenting_problem = models.TextField(
        verbose_name=_("Presenting Problem"),
        blank=True,
        help_text=_("What led to your coming here? What's the major problem?"),
    )

    onset_circumstances = models.TextField(
        verbose_name=_("Onset Circumstances"),
        blank=True,
        help_text=_("What was going on in your life when this began?"),
    )

    last_feeling_ok = models.CharField(
        max_length=100,
        verbose_name=_("Last Feeling OK"),
        blank=True,
        help_text=_("When were you last feeling OK (your usual self)?"),
    )

    # ==========================================================
    # TREATMENT HISTORY
    # ==========================================================

    first_treatment_age = models.CharField(
        max_length=50,
        verbose_name=_("First Treatment Age"),
        blank=True,
        help_text=_("When was the first time you saw someone for emotional or psychiatric problems?"),
    )

    first_treatment_reason = models.TextField(
        verbose_name=_("First Treatment Reason"),
        blank=True,
        help_text=_("What was that for? What treatment(s) did you get?"),
    )

    psychiatric_hospitalization = models.BooleanField(
        default=False,
        verbose_name=_("Psychiatric Hospitalization"),
        help_text=_("Have you ever been a patient in a psychiatric hospital?"),
    )

    hospitalization_count = models.PositiveIntegerField(
        verbose_name=_("Hospitalization Count"),
        blank=True,
        null=True,
        help_text=_("How many times?"),
    )

    hospitalization_reason = models.TextField(
        verbose_name=_("Hospitalization Reason"),
        blank=True,
        help_text=_("What was that for?"),
    )

    substance_treatment = models.BooleanField(
        default=False,
        verbose_name=_("Substance Treatment"),
        help_text=_("Have you ever had any treatment for drugs or alcohol?"),
    )

    treatment_history = models.JSONField(
        verbose_name=_("Treatment History"),
        default=list,
        blank=True,
        help_text=_('List of treatments'),
    )

    # ==========================================================
    # MEDICAL PROBLEMS
    # ==========================================================

    physical_health = models.TextField(
        verbose_name=_("Physical Health"),
        blank=True,
        help_text=_("How has your physical health been?"),
    )

    medical_hospitalization = models.BooleanField(
        default=False,
        verbose_name=_("Medical Hospitalization"),
        help_text=_("Have you ever been in a hospital for treatment of a medical problem?"),
    )

    medical_hospitalization_reason = models.TextField(
        verbose_name=_("Medical Hospitalization Reason"),
        blank=True,
        help_text=_("What was that for?"),
    )

    current_medications = models.TextField(
        verbose_name=_("Current Medications"),
        blank=True,
        help_text=_("What medications are you taking?"),
    )

    # ==========================================================
    # SUICIDAL IDEATION AND BEHAVIOR
    # ==========================================================

    wished_dead = models.BooleanField(
        default=False,
        verbose_name=_("Wished Dead"),
        help_text=_("Have you ever wished you were dead?"),
    )

    wished_dead_details = models.TextField(
        verbose_name=_("Wished Dead Details"),
        blank=True,
        help_text=_("Tell me about that."),
    )

    thoughts_past_week = models.BooleanField(
        default=False,
        verbose_name=_("Thoughts Past Week"),
        help_text=_("Did you have any of these thoughts in the past week?"),
    )

    strong_urge_past_week = models.BooleanField(
        default=False,
        verbose_name=_("Strong Urge Past Week"),
        help_text=_("Have you had a strong urge to kill yourself in the past week?"),
    )

    strong_urge_details = models.TextField(
        verbose_name=_("Strong Urge Details"),
        blank=True,
    )

    intention_past_week = models.BooleanField(
        default=False,
        verbose_name=_("Intention Past Week"),
        help_text=_("Did you have any intention of attempting suicide in the past week?"),
    )

    intention_details = models.TextField(
        verbose_name=_("Intention Details"),
        blank=True,
    )

    plan_past_week = models.BooleanField(
        default=False,
        verbose_name=_("Plan Past Week"),
        help_text=_("Have you thought about how you might do it?"),
    )

    plan_details = models.TextField(
        verbose_name=_("Plan Details"),
        blank=True,
        help_text=_("Tell me about your plan."),
    )

    suicide_attempt = models.BooleanField(
        default=False,
        verbose_name=_("Suicide Attempt"),
        help_text=_("Have you ever tried to kill yourself?"),
    )

    self_harm = models.BooleanField(
        default=False,
        verbose_name=_("Self Harm"),
        help_text=_("Have you ever done anything to harm yourself?"),
    )

    suicide_attempt_details = models.TextField(
        verbose_name=_("Suicide Attempt Details"),
        blank=True,
        help_text=_("Tell me what happened."),
    )

    most_severe_attempt = models.TextField(
        verbose_name=_("Most Severe Attempt"),
        blank=True,
        help_text=_("Which attempt had the most severe consequences?"),
    )

    attempt_past_week = models.BooleanField(
        default=False,
        verbose_name=_("Attempt Past Week"),
        help_text=_("Have you made any attempts in the past week?"),
    )

    # ==========================================================
    # OTHER CURRENT PROBLEMS
    # ==========================================================

    other_problems = models.TextField(
        verbose_name=_("Other Problems"),
        blank=True,
        help_text=_("How are things going at work, at home, and with other people?"),
    )

    mood_description = models.TextField(
        verbose_name=_("Mood Description"),
        blank=True,
        help_text=_("What has your mood been like?"),
    )

    alcohol_use = models.TextField(
        verbose_name=_("Alcohol Use"),
        blank=True,
        help_text=_("How much have you been drinking?"),
    )

    alcohol_with_whom = models.TextField(
        verbose_name=_("Alcohol With Whom"),
        blank=True,
        help_text=_("Who do you drink with?"),
    )

    drug_use = models.TextField(
        verbose_name=_("Drug Use"),
        blank=True,
        help_text=_("Have you been using any drugs?"),
    )

    # ==========================================================
    # METADATA
    # ==========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        verbose_name = _("Overview")
        verbose_name_plural = _("Overviews")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Overview - {self.patient.get_full_name()} - {self.created_at.strftime('%Y-%m-%d')}"


# ============================================================
# PATIENT NOTE MODEL
# ============================================================

class PatientNote(models.Model):
    """
    Notes added by clinicians about the patient.
    """

    NOTE_TYPES = [
        ('general', _('General Note')),
        ('progress', _('Progress Note')),
        ('follow_up', _('Follow-up')),
        ('referral', _('Referral')),
        ('other', _('Other')),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("Patient"),
    )

    clinician = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="patient_notes",
        verbose_name=_("Clinician"),
    )

    content = models.TextField(
        verbose_name=_("Note Content"),
    )

    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPES,
        default='general',
        verbose_name=_("Note Type"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        verbose_name = _("Patient Note")
        verbose_name_plural = _("Patient Notes")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.patient.get_full_name()} by {self.clinician.get_full_name()}"


# ============================================================
# SIGNALS
# ============================================================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.create(user=instance)
        except Exception as e:
            print(f"Error creating profile for {instance.phone_number}: {e}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        try:
            instance.profile.save()
        except Exception:
            pass