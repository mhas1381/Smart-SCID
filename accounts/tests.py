"""
Test cases for accounts app.
Includes model tests, API tests, and integration tests.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from unittest.mock import patch
from .models import User, UserProfile, Patient, PatientNote, Overview

User = get_user_model()


# ============================================================
# MODEL TESTS
# ============================================================

class UserModelTest(TestCase):
    """Test cases for User model."""

    def setUp(self):
        self.phone_number = "09123456789"
        self.password = "Test@1234"
        self.user = User.objects.create_user(
            phone_number=self.phone_number,
            password=self.password,
            first_name="احمد",
            last_name="رضایی",
            email="ahmad@example.com"
        )

    def test_create_user(self):
        """Test creating a user works correctly."""
        self.assertEqual(self.user.phone_number, self.phone_number)
        self.assertTrue(self.user.has_usable_password())
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.first_name, "احمد")
        self.assertEqual(self.user.last_name, "رضایی")
        self.assertEqual(self.user.email, "ahmad@example.com")

    def test_user_str_method(self):
        """Test the string representation of a user."""
        expected = f"{self.user.first_name} {self.user.last_name} ({self.user.phone_number})"
        self.assertEqual(str(self.user), expected)

    def test_user_full_name(self):
        """Test get_full_name method."""
        expected = f"{self.user.first_name} {self.user.last_name}"
        self.assertEqual(self.user.get_full_name(), expected)

    def test_user_phone_unique(self):
        """Test phone number must be unique."""
        with self.assertRaises(Exception):
            User.objects.create_user(
                phone_number=self.phone_number,
                password="Test@1234"
            )

    def test_user_profile_auto_created(self):
        """Test profile is auto-created after user creation."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsNotNone(self.user.profile)
        self.assertEqual(self.user.profile.role, 'clinician')


class PatientModelTest(TestCase):
    """Test cases for Patient model."""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="09123456789",
            password="Test@1234"
        )
        self.patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            phone_number="09123456780",
            created_by=self.user
        )

    def test_create_patient(self):
        """Test creating a patient works correctly."""
        self.assertIsNotNone(self.patient.patient_code)
        self.assertTrue(self.patient.patient_code.startswith('P-'))
        self.assertEqual(self.patient.first_name, "علی")
        self.assertEqual(self.patient.last_name, "محمدی")
        self.assertEqual(self.patient.created_by, self.user)
        self.assertTrue(self.patient.is_active)

    def test_patient_str_method(self):
        """Test the string representation of a patient."""
        expected = f"{self.patient.first_name} {self.patient.last_name} ({self.patient.patient_code})"
        self.assertEqual(str(self.patient), expected)

    def test_patient_full_name(self):
        """Test get_full_name method."""
        expected = f"{self.patient.first_name} {self.patient.last_name}"
        self.assertEqual(self.patient.get_full_name(), expected)

    def test_patient_code_auto_generated(self):
        """Test patient code is auto-generated."""
        code = self.patient.patient_code
        self.assertGreater(len(code), 10)
        self.assertIn('-', code)

    def test_patient_soft_delete(self):
        """Test soft delete sets is_active=False."""
        self.patient.is_active = False
        self.patient.save()
        self.assertFalse(self.patient.is_active)

    def test_patient_created_by_required(self):
        """Test patient must have created_by."""
        with self.assertRaises(Exception):
            Patient.objects.create(
                first_name="Test",
                last_name="Patient"
            )


class PatientNoteModelTest(TestCase):
    """Test cases for PatientNote model."""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="09123456789",
            password="Test@1234"
        )
        self.patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        self.note = PatientNote.objects.create(
            patient=self.patient,
            clinician=self.user,
            content="تست یادداشت",
            note_type="general"
        )

    def test_create_patient_note(self):
        """Test creating a patient note works correctly."""
        self.assertIsNotNone(self.note.id)
        self.assertEqual(self.note.patient, self.patient)
        self.assertEqual(self.note.clinician, self.user)
        self.assertEqual(self.note.content, "تست یادداشت")
        self.assertEqual(self.note.note_type, "general")

    def test_patient_note_str_method(self):
        """Test string representation of patient note."""
        expected = f"Note for {self.patient.get_full_name()} by {self.user.get_full_name()}"
        self.assertEqual(str(self.note), expected)


class OverviewModelTest(TestCase):
    """Test cases for Overview model."""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="09123456789",
            password="Test@1234"
        )
        self.patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        self.overview = Overview.objects.create(
            patient=self.patient,
            clinician=self.user,
            age=35,
            occupation="مهندس نرم‌افزار",
            employment_status="full_time",
            presenting_problem="اضطراب و بی‌خوابی",
            wished_dead=False,
            suicide_attempt=False
        )

    def test_create_overview(self):
        """Test creating an overview works correctly."""
        self.assertIsNotNone(self.overview.id)
        self.assertEqual(self.overview.patient, self.patient)
        self.assertEqual(self.overview.clinician, self.user)
        self.assertEqual(self.overview.age, 35)
        self.assertEqual(self.overview.occupation, "مهندس نرم‌افزار")
        self.assertEqual(self.overview.presenting_problem, "اضطراب و بی‌خوابی")

    def test_overview_str_method(self):
        """Test string representation of overview."""
        expected = f"Overview - {self.patient.get_full_name()} - {self.overview.created_at.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.overview), expected)


# ============================================================
# API TESTS
# ============================================================

class AuthAPITest(TestCase):
    """Test cases for authentication APIs."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/accounts/register/"
        self.token_url = "/api/accounts/token/"
        self.send_otp_url = "/api/accounts/auth/send-otp/"
        self.verify_otp_url = "/api/accounts/auth/verify-otp/"

    def test_register_success(self):
        """Test successful user registration."""
        data = {
            "phone_number": "09123456789",
            "password": "Test@1234",
            "confirm_password": "Test@1234",
            "first_name": "احمد",
            "last_name": "رضایی",
            "email": "ahmad@example.com"
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['phone_number'], "09123456789")
        self.assertEqual(response.data['user']['first_name'], "احمد")
        self.assertEqual(response.data['user']['last_name'], "رضایی")
        self.assertEqual(response.data['message'], "ثبت نام با موفقیت انجام شد.")

    def test_register_duplicate_phone(self):
        """Test registration with duplicate phone number."""
        data = {
            "phone_number": "09123456789",
            "password": "Test@1234",
            "confirm_password": "Test@1234"
        }
        self.client.post(self.register_url, data, format='json')
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.data)

    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = {
            "phone_number": "09123456789",
            "password": "Test@1234",
            "confirm_password": "Test@12345"
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('confirm_password', response.data)

    def test_register_invalid_phone(self):
        """Test registration with invalid phone format."""
        data = {
            "phone_number": "1234567890",
            "password": "Test@1234",
            "confirm_password": "Test@1234"
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.data)

    def test_login_success(self):
        """Test successful login."""
        register_data = {
            "phone_number": "09123456789",
            "password": "Test@1234",
            "confirm_password": "Test@1234"
        }
        self.client.post(self.register_url, register_data, format='json')

        login_data = {
            "phone_number": "09123456789",
            "password": "Test@1234"
        }
        response = self.client.post(self.token_url, login_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['phone_number'], "09123456789")

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        login_data = {
            "phone_number": "09123456789",
            "password": "WrongPassword"
        }
        response = self.client.post(self.token_url, login_data, format='json')
        self.assertEqual(response.status_code, 401)

    @patch('utils.sms.send_verification_code')
    def test_send_otp_success(self, mock_send_sms):
        """Test sending OTP successfully."""
        mock_send_sms.return_value = True
        data = {"phone_number": "09123456789"}
        response = self.client.post(self.send_otp_url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], "کد تایید ارسال شد.")
        self.assertIn('user_exists', response.data)

    def test_send_otp_invalid_phone(self):
        """Test sending OTP with invalid phone."""
        data = {"phone_number": "1234567890"}
        response = self.client.post(self.send_otp_url, data, format='json')
        self.assertEqual(response.status_code, 400)

    @patch('utils.sms.send_verification_code')
    def test_verify_otp_new_user(self, mock_send_sms):
        """Test OTP verification for new user."""
        mock_send_sms.return_value = True

        phone = "09123456789"
        self.client.post(self.send_otp_url, {"phone_number": phone}, format='json')

        cache_key = f"otp_{phone}"
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached)
        otp_code = cached['code']

        verify_data = {
            "phone_number": phone,
            "otp_code": otp_code
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('is_new_user', response.data)


class PatientAPITest(TestCase):
    """Test cases for Patient APIs."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number="09123456789",
            password="Test@1234"
        )
        UserProfile.objects.get_or_create(user=self.user, defaults={"role": "clinician"})

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.patients_url = "/api/accounts/patients/"

    def test_create_patient_success(self):
        """Test creating a patient successfully."""
        data = {
            "first_name": "علی",
            "last_name": "محمدی",
            "phone_number": "09123456780",
            "occupation": "مهندس"
        }
        response = self.client.post(self.patients_url, data, format='json')
        
        # Debug if fails
        if response.status_code != 201:
            print("\n" + "="*50)
            print("PATIENT CREATE ERROR:")
            print(f"Status: {response.status_code}")
            print(f"Data: {response.data}")
            print("="*50 + "\n")
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data.get('first_name'), "علی")
        self.assertEqual(response.data.get('last_name'), "محمدی")
        self.assertIsNotNone(response.data.get('patient_code'))

    def test_list_patients(self):
        """Test listing patients."""
        Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        Patient.objects.create(
            first_name="سارا",
            last_name="احمدی",
            created_by=self.user
        )

        response = self.client.get(self.patients_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_patients_only_own(self):
        """Test user can only see their own patients."""
        user2 = User.objects.create_user(
            phone_number="09123456788",
            password="Test@1234"
        )
        Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        Patient.objects.create(
            first_name="رضا",
            last_name="کریمی",
            created_by=user2
        )

        response = self.client.get(self.patients_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0].get('full_name'), "علی محمدی")

    def test_get_patient_detail(self):
        """Test getting patient details."""
        patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        response = self.client.get(f"{self.patients_url}{patient.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['first_name'], "علی")
        self.assertEqual(response.data['last_name'], "محمدی")

    def test_update_patient(self):
        """Test updating a patient."""
        patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        data = {"occupation": "مهندس ارشد"}
        response = self.client.patch(f"{self.patients_url}{patient.id}/", data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['occupation'], "مهندس ارشد")

    def test_delete_patient_soft(self):
        """Test soft deleting a patient."""
        patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        response = self.client.delete(f"{self.patients_url}{patient.id}/")
        self.assertEqual(response.status_code, 204)

        patient.refresh_from_db()
        self.assertFalse(patient.is_active)


class PatientNoteAPITest(TestCase):
    """Test cases for Patient Note APIs."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number="09123456789",
            password="Test@1234"
        )
        UserProfile.objects.get_or_create(user=self.user, defaults={"role": "clinician"})

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        self.notes_url = f"/api/accounts/patients/{self.patient.id}/notes/"

    def test_create_patient_note(self):
        """Test creating a patient note."""
        data = {
            "content": "تست یادداشت",
            "note_type": "general"
        }
        response = self.client.post(self.notes_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['content'], "تست یادداشت")
        self.assertEqual(response.data['note_type'], "general")

    def test_list_patient_notes(self):
        """Test listing patient notes."""
        PatientNote.objects.create(
            patient=self.patient,
            clinician=self.user,
            content="یادداشت اول"
        )
        PatientNote.objects.create(
            patient=self.patient,
            clinician=self.user,
            content="یادداشت دوم"
        )

        response = self.client.get(self.notes_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_unauthorized_note_access(self):
        """Test user cannot access notes of other user's patient."""
        user2 = User.objects.create_user(
            phone_number="09123456788",
            password="Test@1234"
        )
        refresh = RefreshToken.for_user(user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = self.client.get(self.notes_url)
        self.assertEqual(response.status_code, 404)


class OverviewAPITest(TestCase):
    """Test cases for Overview APIs."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number="09123456789",
            password="Test@1234"
        )
        UserProfile.objects.get_or_create(user=self.user, defaults={"role": "clinician"})

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.patient = Patient.objects.create(
            first_name="علی",
            last_name="محمدی",
            created_by=self.user
        )
        self.overviews_url = f"/api/accounts/patients/{self.patient.id}/overviews/"

    def test_create_overview_success(self):
        """Test creating an overview successfully."""
        data = {
            "age": 35,
            "occupation": "مهندس نرم‌افزار",
            "employment_status": "full_time",
            "presenting_problem": "اضطراب و بی‌خوابی",
            "wished_dead": False,
            "suicide_attempt": False,
            "self_harm": False
        }
        response = self.client.post(self.overviews_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['patient'], self.patient.id)
        self.assertEqual(response.data['clinician'], self.user.id)
        self.assertEqual(response.data['message'], "Overview created successfully")

    def test_list_overviews(self):
        """Test listing overviews."""
        Overview.objects.create(
            patient=self.patient,
            clinician=self.user,
            age=35,
            occupation="مهندس"
        )
        Overview.objects.create(
            patient=self.patient,
            clinician=self.user,
            age=40,
            occupation="دکتر"
        )

        response = self.client.get(self.overviews_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_overview_detail(self):
        """Test getting overview details."""
        overview = Overview.objects.create(
            patient=self.patient,
            clinician=self.user,
            age=35,
            occupation="مهندس نرم‌افزار",
            presenting_problem="اضطراب"
        )
        response = self.client.get(f"/api/accounts/overviews/{overview.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['age'], 35)
        self.assertEqual(response.data['occupation'], "مهندس نرم‌افزار")

    def test_update_overview(self):
        """Test updating an overview."""
        overview = Overview.objects.create(
            patient=self.patient,
            clinician=self.user,
            age=35,
            occupation="مهندس"
        )
        data = {"occupation": "مهندس ارشد"}
        response = self.client.patch(f"/api/accounts/overviews/{overview.id}/", data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['occupation'], "مهندس ارشد")

    def test_overview_branching_logic(self):
        """Test suicidal ideation branching logic."""
        data = {
            "age": 35,
            "wished_dead": True,
            "wished_dead_details": "Sometimes I feel hopeless",
            "thoughts_past_week": True,
            "strong_urge_past_week": False,
            "intention_past_week": False,
            "plan_past_week": False,
            "suicide_attempt": True,
            "suicide_attempt_details": "Took pills 2 years ago",
            "most_severe_attempt": "Hospitalized for 3 days"
        }
        response = self.client.post(self.overviews_url, data, format='json')
        self.assertEqual(response.status_code, 201)

        overview_id = response.data['id']
        overview = Overview.objects.get(id=overview_id)
        self.assertTrue(overview.wished_dead)
        self.assertTrue(overview.thoughts_past_week)
        self.assertFalse(overview.strong_urge_past_week)
        self.assertTrue(overview.suicide_attempt)
        self.assertIsNotNone(overview.suicide_attempt_details)

    def test_unauthorized_overview_access(self):
        """Test user cannot access overviews of other user's patient."""
        user2 = User.objects.create_user(
            phone_number="09123456788",
            password="Test@1234"
        )
        refresh = RefreshToken.for_user(user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = self.client.get(self.overviews_url)
        self.assertEqual(response.status_code, 404)


class IntegrationTest(TestCase):
    """Integration tests for complete workflow."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/accounts/register/"
        self.token_url = "/api/accounts/token/"
        self.patients_url = "/api/accounts/patients/"
        self.overviews_url_base = "/api/accounts/patients/{}/overviews/"

    def test_full_workflow(self):
        """Test complete workflow: register -> login -> create patient -> create overview."""

        # 1. Register
        register_data = {
            "phone_number": "09123456789",
            "password": "Test@1234",
            "confirm_password": "Test@1234",
            "first_name": "احمد",
            "last_name": "رضایی"
        }
        register_response = self.client.post(self.register_url, register_data, format='json')
        self.assertEqual(register_response.status_code, 201)
        access_token = register_response.data['access']

        # 2. Authenticate client
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # 3. Create patient
        patient_data = {
            "first_name": "علی",
            "last_name": "محمدی",
            "phone_number": "09123456780"
        }
        patient_response = self.client.post(self.patients_url, patient_data, format='json')
        
        # Debug if fails
        if patient_response.status_code != 201:
            print("\n" + "="*50)
            print("FULL WORKFLOW - PATIENT CREATE ERROR:")
            print(f"Status: {patient_response.status_code}")
            print(f"Data: {patient_response.data}")
            print("="*50 + "\n")
        
        self.assertEqual(patient_response.status_code, 201)

        # Get patient ID from response
        patient_id = patient_response.data.get('id')
        self.assertIsNotNone(patient_id)

        # 4. Create overview
        overviews_url = self.overviews_url_base.format(patient_id)
        overview_data = {
            "age": 35,
            "occupation": "مهندس",
            "employment_status": "full_time",
            "presenting_problem": "اضطراب",
            "wished_dead": False,
            "suicide_attempt": False
        }
        overview_response = self.client.post(overviews_url, overview_data, format='json')
        self.assertEqual(overview_response.status_code, 201)

        # 5. List overviews
        list_response = self.client.get(overviews_url)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data['count'], 1)

        # 6. Verify patient has overview
        overview_id = overview_response.data['id']
        self.assertIsNotNone(overview_id)

        print("✅ Full workflow test passed successfully!")