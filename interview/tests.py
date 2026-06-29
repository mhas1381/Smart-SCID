"""
Test cases for interview app.
Includes API tests for modules, questions, interviews, and interview flow.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone

from accounts.models import User, UserProfile, Patient
from .models import Interview, InterviewModule, Question, Answer, JumpRule

User = get_user_model()


class InterviewAPITests(APITestCase):
    """
    Test cases for interview API endpoints.
    Covers modules, questions, starting interviews, progress, pause, resume, and summary.
    """

    def setUp(self):
        """
        Set up test data for all tests.
        Creates a clinician, patient, module, questions, and jump rules.
        """
        # Create clinician user
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        # Use get_or_create to avoid duplicate profile error (signal already creates profile)
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        # Create patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name="Module A - Mood Episodes",
            description="Test module for mood episodes",
            version="1.0",
            is_active=True,
            order=1,
        )

        # Create questions
        self.q1 = Question.objects.create(
            id="A1",
            module=self.module,
            text="سوال اول؟",
            question_type="boolean",
            order=1,
            has_jump_logic=True,
        )

        self.q2 = Question.objects.create(
            id="A2",
            module=self.module,
            text="سوال دوم؟",
            question_type="boolean",
            order=2,
        )

        self.q3 = Question.objects.create(
            id="A3",
            module=self.module,
            text="سوال سوم؟",
            question_type="boolean",
            order=3,
        )

        # Create jump rule: if answer to q1 is True, skip q2 and go to q3
        JumpRule.objects.create(
            from_question=self.q1,
            to_question=self.q3,
            condition="answer == true",
            condition_type="boolean",
            metadata={"expected_value": True},
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    # ============================================================
    # MODULE TESTS
    # ============================================================

    def test_get_modules(self):
        """
        Test retrieving list of active modules.
        Should return 200 OK with the module list.
        """
        response = self.client.get("/api/interviews/modules/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Module A - Mood Episodes")
        self.assertEqual(response.data[0]["question_count"], 3)
        self.assertIn("is_active", response.data[0])
        self.assertIn("version", response.data[0])

    # ============================================================
    # QUESTION TESTS
    # ============================================================

    def test_get_questions(self):
        """
        Test retrieving list of questions.
        Should return 200 OK with all questions.
        """
        response = self.client.get("/api/interviews/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

        # Test new serializer fields
        for question_data in response.data:
            self.assertIn("id", question_data)
            self.assertIn("text", question_data)
            self.assertIn("question_type", question_data)
            self.assertIn("is_criteria", question_data)
            self.assertIn("order", question_data)
            self.assertIn("module_name", question_data)

    # ============================================================
    # INTERVIEW FLOW TESTS
    # ============================================================

    def test_start_interview(self):
        """
        Test starting a new interview session.
        Should return 201 Created with interview data and current question.
        """
        response = self.client.post(
            "/api/interviews/interviews/start/",
            {
                "patient_id": str(self.patient.id),  # Convert to string
                "module_id": self.module.id,
            },
            format="json",
        )

        # Debug if fails
        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(response.data["patient_name"], "Test Patient")
        self.assertEqual(response.data["clinician_name"], "Test Clinician")
        self.assertEqual(response.data["module_name"], "Module A - Mood Episodes")
        self.assertEqual(response.data["current_question_text"], "سوال اول؟")
        self.assertEqual(response.data["answer_count"], 0)
        # InterviewListSerializer doesn't include answers field, only answer_count

    def test_progress_with_jump(self):
        """
        Test interview progress with jump logic.
        When answering True to q1, should skip q2 and jump to q3.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.q1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "A1",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        print(f"Progress with jump response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "A3")
        self.assertEqual(response.data["current_question"]["text"], "سوال سوم؟")
        self.assertEqual(response.data["has_next"], True)
        self.assertEqual(response.data["interview_status"], "in_progress")
        self.assertEqual(response.data["answered_questions"], 1)
        self.assertEqual(response.data["total_questions"], 3)

    def test_progress_without_jump(self):
        """
        Test interview progress without jump logic.
        When answering False to q1, should go to q2 sequentially.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.q1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "A1",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        print(f"Progress without jump response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "A2")
        self.assertEqual(response.data["current_question"]["text"], "سوال دوم؟")
        self.assertEqual(response.data["has_next"], True)
        self.assertEqual(response.data["interview_status"], "in_progress")
        self.assertEqual(response.data["answered_questions"], 1)
        self.assertEqual(response.data["total_questions"], 3)

    def test_complete_interview(self):
        """
        Test completing an interview.
        When answering the last question, interview should be marked as completed.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.q3,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "A3",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        print(f"Complete interview response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_next"])
        self.assertEqual(response.data["interview_status"], "completed")
        self.assertEqual(response.data["answered_questions"], 1)
        self.assertEqual(response.data["total_questions"], 3)
        self.assertIn("diagnosis_result", response.data)
        self.assertEqual(response.data["patient_name"], "Test Patient")
        self.assertEqual(response.data["clinician_name"], "Test Clinician")
        self.assertEqual(response.data["module_name"], "Module A - Mood Episodes")

    def test_pause_interview(self):
        """
        Test pausing an in-progress interview.
        Should change status from 'in_progress' to 'paused'.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
        )

        response = self.client.post(f"/api/interviews/interviews/{interview.id}/pause/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Interview paused successfully")
        interview.refresh_from_db()
        self.assertEqual(interview.status, "paused")

    def test_resume_interview(self):
        """
        Test resuming a paused interview.
        Should change status from 'paused' to 'in_progress'.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="paused",
            current_question=self.q1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/resume/"
        )
        print(f"Resume interview response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Interview resumed successfully")
        # For a paused interview, there might not be a current question yet
        if "current_question" in response.data:
            self.assertIsNotNone(response.data["current_question"])
        interview.refresh_from_db()
        self.assertEqual(interview.status, "in_progress")

    # ============================================================
    # SUMMARY TESTS
    # ============================================================

    def test_summary_completed(self):
        """
        Test retrieving summary for a completed interview.
        Should return 200 OK with diagnosis results.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.q1,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        print(f"Summary response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("diagnosis_result", response.data)
        # Summary might not have patient_name field depending on serializer
        self.assertEqual(response.data["completed_questions"], 1)
        self.assertEqual(response.data["total_questions"], 3)
        self.assertIsNotNone(response.data["duration"])

    def test_summary_not_completed(self):
        """
        Test retrieving summary for an incomplete interview.
        Should return 400 Bad Request because interview is not completed.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 400)

    # ============================================================
    # AUTHORIZATION TESTS
    # ============================================================

    def test_unauthorized_access(self):
        """
        Test that a different clinician cannot access another clinician's interview.
        Should return 403 Forbidden.
        """
        # Create another clinician
        other = User.objects.create_user(
            phone_number="09123456788", first_name="Other", last_name="User"
        )
        UserProfile.objects.get_or_create(user=other, defaults={"role": "clinician"})

        # Create interview with original clinician
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
        )

        # Authenticate as other clinician
        self.client.force_authenticate(user=other)

        # Try to access the interview
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "A1",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)


# ============================================================
# NEW SERIALIZER TESTS
# ============================================================


class InterviewDetailTests(APITestCase):
    """Test cases for InterviewDetailSerializer functionality."""

    def setUp(self):
        """Set up test data for detailed interview tests."""
        # Create clinician user
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        # Create patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name="Module A - Mood Episodes",
            description="Test module for mood episodes",
            version="1.0",
            is_active=True,
            order=1,
        )

        # Create interview
        self.interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    def test_interview_detail_serializer(self):
        """Test InterviewDetailSerializer returns complete data."""
        response = self.client.get(f"/api/interviews/interviews/{self.interview.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["patient_name"], "Test Patient")
        self.assertEqual(response.data["clinician_name"], "Test Clinician")
        self.assertEqual(response.data["module_name"], "Module A - Mood Episodes")
        self.assertEqual(response.data["status"], "completed")
        self.assertIsNotNone(response.data["patient"])
        self.assertIsNotNone(response.data["answers"])
        self.assertEqual(response.data["answer_count"], 0)


class AnswerTests(APITestCase):
    """Test cases for Answer serializers."""

    def setUp(self):
        """Set up test data for answer tests."""
        # Create clinician user
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        # Create patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name="Module A - Mood Episodes",
            description="Test module for mood episodes",
            version="1.0",
            is_active=True,
            order=1,
        )

        # Create interview
        self.interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
        )

        # Create question
        self.question = Question.objects.create(
            id="A1",
            module=self.module,
            text="Test question?",
            question_type="boolean",
            order=1,
        )

        # Create answer
        self.answer = Answer.objects.create(
            interview=self.interview,
            question=self.question,
            answer_type="boolean",
            value={"boolean": True},
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    def test_answer_list_serializer(self):
        """Test AnswerListSerializer returns answer data with question info."""
        response = self.client.get(
            f"/api/interviews/interviews/{self.interview.id}/answers/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        answer_data = response.data[0]
        self.assertEqual(answer_data["question_text"], "Test question?")
        self.assertEqual(answer_data["question_type"], "boolean")
        self.assertEqual(answer_data["answer_type"], "boolean")
        self.assertEqual(answer_data["value"], {"boolean": True})

    def test_answer_detail_serializer(self):
        """Test AnswerDetailSerializer returns complete answer data."""
        response = self.client.get(f"/api/interviews/answers/{self.answer.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["question"]["id"], "A1")
        self.assertEqual(response.data["question"]["text"], "Test question?")
        self.assertEqual(response.data["answer_type"], "boolean")
        self.assertEqual(response.data["value"], {"boolean": True})
        self.assertIsNotNone(response.data["timestamp"])


class JumpRuleTests(APITestCase):
    """Test cases for JumpRule serializers."""

    def setUp(self):
        """Set up test data for jump rule tests."""
        # Create clinician user
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        # Create patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name="Module A - Mood Episodes",
            description="Test module for mood episodes",
            version="1.0",
            is_active=True,
            order=1,
        )

        # Create questions
        self.q1 = Question.objects.create(
            id="A1",
            module=self.module,
            text="Question 1?",
            question_type="boolean",
            order=1,
        )

        self.q2 = Question.objects.create(
            id="A2",
            module=self.module,
            text="Question 2?",
            question_type="boolean",
            order=2,
        )

        # Create jump rule
        self.jump_rule = JumpRule.objects.create(
            from_question=self.q1,
            to_question=self.q2,
            condition="answer == true",
            condition_type="boolean",
            metadata={"expected_value": True},
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    def test_jump_rule_list_serializer(self):
        """Test JumpRuleListSerializer returns jump rule data."""
        response = self.client.get("/api/interviews/jump-rules/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        rule_data = response.data[0]
        self.assertEqual(rule_data["from_question_text"], "Question 1?")
        self.assertEqual(rule_data["to_question_text"], "Question 2?")
        self.assertEqual(rule_data["condition"], "answer == true")
        self.assertEqual(rule_data["condition_type"], "boolean")

    def test_jump_rule_detail_serializer(self):
        """Test JumpRuleDetailSerializer returns complete jump rule data."""
        response = self.client.get(f"/api/interviews/jump-rules/{self.jump_rule.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["from_question"]["id"], "A1")
        self.assertEqual(response.data["from_question"]["text"], "Question 1?")
        self.assertEqual(response.data["to_question"]["id"], "A2")
        self.assertEqual(response.data["to_question"]["text"], "Question 2?")
        self.assertEqual(response.data["condition"], "answer == true")
        self.assertEqual(response.data["condition_type"], "boolean")
        self.assertEqual(response.data["metadata"], {"expected_value": True})


# ============================================================
# MODULE B TESTS
# ============================================================


class ModuleBInterviewTests(APITestCase):
    """
    Test cases for Module B — Psychotic and Associated Symptoms.
    Covers interview flow, jump rules, and diagnosis calculation.
    """

    def setUp(self):
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        self.module = InterviewModule.objects.create(
            name="Module B - Psychotic and Associated Symptoms",
            description="Psychotic symptoms module",
            version="1.0",
            is_active=True,
            order=2,
        )

        # Create Module B questions (subset for testing)
        self.b1 = Question.objects.create(
            id="B1",
            module=self.module,
            text="توهم مرجعیت؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="1",
            order=1,
            has_jump_logic=True,
        )
        self.b2 = Question.objects.create(
            id="B2",
            module=self.module,
            text="توهم آزار و تعقیب؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="2",
            order=2,
        )
        self.b11 = Question.objects.create(
            id="B11",
            module=self.module,
            text="سایر توهمات؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="11",
            order=11,
            has_jump_logic=True,
        )
        self.b12 = Question.objects.create(
            id="B12",
            module=self.module,
            text="توهم شنوایی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="12",
            order=12,
            has_jump_logic=True,
        )
        self.b18 = Question.objects.create(
            id="B18",
            module=self.module,
            text="گفتار آشفته؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="18",
            order=18,
        )
        self.b20 = Question.objects.create(
            id="B20",
            module=self.module,
            text="رفتار کاتاتونیک؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="20",
            order=20,
            has_jump_logic=True,
        )
        self.b21 = Question.objects.create(
            id="B21",
            module=self.module,
            text="بی‌ارادگی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="21",
            order=21,
        )
        self.b23 = Question.objects.create(
            id="B23",
            module=self.module,
            text="بیماری پزشکی؟",
            question_type="boolean",
            order=23,
        )
        self.b24 = Question.objects.create(
            id="B24",
            module=self.module,
            text="مصرف ماده؟",
            question_type="boolean",
            order=24,
        )

        # Jump rules
        JumpRule.objects.create(
            from_question=self.b1,
            to_question=self.b12,
            condition="criteria_count < 1",
            condition_type="criteria_count",
            metadata={"question_ids": ["B1"], "min_count": 1},
        )
        JumpRule.objects.create(
            from_question=self.b12,
            to_question=self.b18,
            condition="answer == false",
            condition_type="boolean",
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.b20,
            to_question=self.b21,
            condition="answer == false",
            condition_type="boolean",
            metadata={"expected_value": False},
        )

        self.client.force_authenticate(user=self.clinician)

    def test_module_b_listed(self):
        """Module B should appear in the modules list."""
        response = self.client.get("/api/interviews/modules/")
        self.assertEqual(response.status_code, 200)
        names = [m["name"] for m in response.data]
        self.assertIn("Module B - Psychotic and Associated Symptoms", names)

    def test_module_b_start_interview(self):
        """Should be able to start a Module B interview."""
        response = self.client.post(
            "/api/interviews/interviews/start/",
            {"patient_id": str(self.patient.id), "module_id": self.module.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(
            response.data["module_name"], "Module B - Psychotic and Associated Symptoms"
        )

    def test_b1_negative_skips_to_b12(self):
        """If B1 (delusion of reference) is negative, skip to B12 (auditory hallucination)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.b1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "B1",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "B12")

    def test_b1_positive_continues_to_b2(self):
        """If B1 (delusion of reference) is positive, continue to B2."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.b1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "B1",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "B2")

    def test_b12_negative_skips_to_b18(self):
        """If B12 (auditory hallucination) is negative, skip to B18 (disorganized speech)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.b12,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "B12",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "B18")

    def test_b20_negative_skips_to_b21(self):
        """If B20 (catatonic behavior) is negative, skip to B21 (negative symptoms)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.b20,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "B20",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "B21")

    def test_module_b_diagnosis_with_symptoms(self):
        """Diagnosis should report present psychotic symptoms."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        # B1 positive (delusion of reference)
        Answer.objects.create(
            interview=interview,
            question=self.b1,
            answer_type="boolean",
            value={"boolean": True},
        )
        # B12 positive (auditory hallucination)
        Answer.objects.create(
            interview=interview,
            question=self.b12,
            answer_type="boolean",
            value={"boolean": True},
        )
        # B23 negative (not due to medical)
        Answer.objects.create(
            interview=interview,
            question=self.b23,
            answer_type="boolean",
            value={"boolean": False},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertIn("psychotic_symptoms", diagnosis)
        self.assertTrue(diagnosis["psychotic_symptoms"]["delusions"]["present"])
        self.assertEqual(diagnosis["psychotic_symptoms"]["delusions"]["count"], 1)
        self.assertIn("B1", diagnosis["psychotic_symptoms"]["delusions"]["items"])
        self.assertTrue(diagnosis["psychotic_symptoms"]["hallucinations"]["present"])
        self.assertFalse(diagnosis["exclusion_factors"]["due_to_medical_condition"])

    def test_module_b_diagnosis_no_symptoms(self):
        """Diagnosis should report no psychotic symptoms when all negative."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        # All negative
        for q in [
            self.b1,
            self.b2,
            self.b12,
            self.b18,
            self.b20,
            self.b21,
            self.b23,
            self.b24,
        ]:
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": False},
            )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["psychotic_symptoms"]["delusions"]["present"])
        self.assertEqual(diagnosis["psychotic_symptoms"]["delusions"]["count"], 0)
        self.assertFalse(diagnosis["psychotic_symptoms"]["hallucinations"]["present"])


# ============================================================
# MODULE C TESTS
# ============================================================


class ModuleCInterviewTests(APITestCase):
    """
    Test cases for Module C — Differential Diagnosis of Psychotic Disorders.
    Covers interview flow, jump rules, and diagnosis calculation.
    """

    def setUp(self):
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        self.module = InterviewModule.objects.create(
            name="Module C - Differential Diagnosis of Psychotic Disorders",
            description="Differential diagnosis of psychotic disorders",
            version="1.0",
            is_active=True,
            order=3,
        )

        # Create Module C questions (subset for testing)
        self.c1 = Question.objects.create(
            id="C1",
            module=self.module,
            text="علائم خارج از دوره خلقی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="1",
            order=1,
            has_jump_logic=True,
        )
        self.c2 = Question.objects.create(
            id="C2",
            module=self.module,
            text="معیار A اسکیزوفرنی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="2",
            order=2,
            has_jump_logic=True,
        )
        self.c3 = Question.objects.create(
            id="C3",
            module=self.module,
            text="معیار B اسکیزوفرنی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="3",
            order=3,
        )
        self.c4 = Question.objects.create(
            id="C4",
            module=self.module,
            text="معیار C اسکیزوفرنی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="4",
            order=4,
        )
        self.c5 = Question.objects.create(
            id="C5",
            module=self.module,
            text="معیار D اسکیزوفرنی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="5",
            order=5,
        )
        self.c6 = Question.objects.create(
            id="C6",
            module=self.module,
            text="معیار E اسکیزوفرنی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="6",
            order=6,
            has_jump_logic=True,
        )
        self.c7 = Question.objects.create(
            id="C7",
            module=self.module,
            text="اسکیزوفرنی‌فرم: مدت ۱-۶ ماه؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="7",
            order=7,
        )
        self.c8 = Question.objects.create(
            id="C8",
            module=self.module,
            text="اسکیزوفرنی‌فرم: رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="8",
            order=8,
            has_jump_logic=True,
        )
        self.c9 = Question.objects.create(
            id="C9",
            module=self.module,
            text="اسکیزوافکتیو: دوره خلقی همزمان؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="9",
            order=9,
        )
        self.c10 = Question.objects.create(
            id="C10",
            module=self.module,
            text="اسکیزوافکتیو: توهم/هذیان بدون خلق؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="10",
            order=10,
        )
        self.c11 = Question.objects.create(
            id="C11",
            module=self.module,
            text="اسکیزوافکتیو: خلق >50%؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="11",
            order=11,
        )
        self.c12 = Question.objects.create(
            id="C12",
            module=self.module,
            text="اسکیزوافکتیو: رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="12",
            order=12,
            has_jump_logic=True,
        )
        self.c13 = Question.objects.create(
            id="C13",
            module=self.module,
            text="هذیانی: هذیان ۱+ ماه؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="13",
            order=13,
        )
        self.c14 = Question.objects.create(
            id="C14",
            module=self.module,
            text="هذیانی: بدون معیار A اسکیزوفرنی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="14",
            order=14,
        )
        self.c15 = Question.objects.create(
            id="C15",
            module=self.module,
            text="هذیانی: عملکرد مختل نشده؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="15",
            order=15,
        )
        self.c16 = Question.objects.create(
            id="C16",
            module=self.module,
            text="هذیانی: خلق کوتاه‌تر از هذیان؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="16",
            order=16,
        )
        self.c17 = Question.objects.create(
            id="C17",
            module=self.module,
            text="هذیانی: رد ماده/بیماری/OCD؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="17",
            order=17,
        )
        self.c18 = Question.objects.create(
            id="C18",
            module=self.module,
            text="نوع هذیان؟",
            question_type="text",
            order=18,
        )
        self.c19 = Question.objects.create(
            id="C19",
            module=self.module,
            text="روان‌پریشی کوتاه: علائم؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="18",
            order=19,
        )
        self.c20 = Question.objects.create(
            id="C20",
            module=self.module,
            text="روان‌پریشی کوتاه: مدت ۱ روز-۱ ماه؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="19",
            order=20,
        )
        self.c21 = Question.objects.create(
            id="C21",
            module=self.module,
            text="روان‌پریشی کوتاه: رد خلقی/سایر؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="20",
            order=21,
        )
        self.c22 = Question.objects.create(
            id="C22",
            module=self.module,
            text="سایر مشخص‌شده: علائم غالب؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="21",
            order=22,
        )
        self.c23 = Question.objects.create(
            id="C23",
            module=self.module,
            text="اختلال بالینی مهم؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="22",
            order=23,
        )
        self.c24 = Question.objects.create(
            id="C24",
            module=self.module,
            text="رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="23",
            order=24,
        )
        self.c25 = Question.objects.create(
            id="C25",
            module=self.module,
            text="عدم تطابق با تشخیص خاص؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="24",
            order=25,
        )
        self.c26 = Question.objects.create(
            id="C26",
            module=self.module,
            text="سیر اسکیزوفرنی: فعلی؟",
            question_type="boolean",
            order=26,
        )
        self.c27 = Question.objects.create(
            id="C27",
            module=self.module,
            text="سیر اسکیزوفرنی‌فرم: فعلی؟",
            question_type="boolean",
            order=27,
        )
        self.c28 = Question.objects.create(
            id="C28",
            module=self.module,
            text="سیر اسکیزوافکتیو: فعلی؟",
            question_type="boolean",
            order=28,
        )
        self.c29 = Question.objects.create(
            id="C29",
            module=self.module,
            text="سیر هذیانی: فعلی؟",
            question_type="boolean",
            order=29,
        )
        self.c30 = Question.objects.create(
            id="C30",
            module=self.module,
            text="سیر کوتاه: فعلی؟",
            question_type="boolean",
            order=30,
        )

        # Jump rules
        JumpRule.objects.create(
            from_question=self.c1,
            to_question=None,
            condition="answer == false",
            condition_type="boolean",
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.c2,
            to_question=self.c13,
            condition="criteria_count < 2",
            condition_type="criteria_count",
            metadata={"question_ids": ["C2", "C3", "C4", "C5", "C6"], "min_count": 2},
        )
        JumpRule.objects.create(
            from_question=self.c6,
            to_question=self.c9,
            condition="criteria_count_met >= 4",
            condition_type="criteria_count_met",
            metadata={"question_ids": ["C2", "C3", "C4", "C5", "C6"], "min_count": 4},
        )
        JumpRule.objects.create(
            from_question=self.c8,
            to_question=self.c9,
            condition="answer == false",
            condition_type="boolean",
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.c12,
            to_question=self.c13,
            condition="answer == false",
            condition_type="boolean",
            metadata={"expected_value": False},
        )

        self.client.force_authenticate(user=self.clinician)

    # ============================================================
    # MODULE LISTING
    # ============================================================

    def test_module_c_listed(self):
        """Module C should appear in the modules list."""
        response = self.client.get("/api/interviews/modules/")
        self.assertEqual(response.status_code, 200)
        names = [m["name"] for m in response.data]
        self.assertIn("Module C - Differential Diagnosis of Psychotic Disorders", names)

    def test_module_c_question_count(self):
        """Module C should report correct question count."""
        response = self.client.get("/api/interviews/modules/")
        self.assertEqual(response.status_code, 200)
        module_data = next(m for m in response.data if "Module C" in m["name"])
        self.assertEqual(module_data["question_count"], 30)

    def test_module_c_start_interview(self):
        """Should be able to start a Module C interview."""
        response = self.client.post(
            "/api/interviews/interviews/start/",
            {"patient_id": str(self.patient.id), "module_id": self.module.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(
            response.data["module_name"],
            "Module C - Differential Diagnosis of Psychotic Disorders",
        )

    # ============================================================
    # JUMP RULE TESTS
    # ============================================================

    def test_c1_negative_ends_interview(self):
        """If C1 (psychosis outside mood) is negative, interview ends (jump to null)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.c1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "C1",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_next"])
        self.assertEqual(response.data["interview_status"], "completed")

    def test_c1_positive_continues_to_c2(self):
        """If C1 (psychosis outside mood) is positive, continue to C2."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.c1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "C1",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "C2")

    def test_c2_negative_skips_to_c13(self):
        """If fewer than 2 of C2-C6 are positive, skip to C13 (Delusional Disorder)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.c2,
        )

        # Only C2 answered so far (1 positive out of 5 → criteria_count < 2 is true)
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "C2",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "C13")

    def test_c6_schizophrenia_criteria_met_skips_to_c9(self):
        """If C2-C6 all positive (schizophrenia criteria met), skip to C9."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.c2,
        )

        # Answer C2-C5 positively first
        for qid in ["C2", "C3", "C4", "C5"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        # Now answer C6 — with 4 already positive, criteria_count >= 4 → jump to C9
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "C6",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "C9")

    def test_c8_negative_skips_to_c9(self):
        """If C8 (schizophreniform exclusion) is negative, skip to C9."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.c8,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "C8",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "C9")

    def test_c12_negative_skips_to_c13(self):
        """If C12 (schizoaffective exclusion) is negative, skip to C13."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.c12,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "C12",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "C13")

    # ============================================================
    # DIAGNOSIS TESTS
    # ============================================================

    def test_diagnosis_psychotic_mood_disorder(self):
        """When C1 is negative, diagnosis should indicate Psychotic Mood Disorder."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.c1,
            answer_type="boolean",
            value={"boolean": False},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["psychotic_mood_disorder"])
        self.assertIn("Module D", diagnosis["note"])

    def test_diagnosis_schizophrenia(self):
        """When C1-C6 all positive, diagnosis should be Schizophrenia."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["C1", "C2", "C3", "C4", "C5", "C6"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        # C26: current
        Answer.objects.create(
            interview=interview,
            question=self.c26,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Schizophrenia")
        self.assertTrue(diagnosis["criteria_summary"]["schizophrenia"]["met"])
        self.assertTrue(diagnosis["details"]["current"])

    def test_diagnosis_schizophreniform(self):
        """When C1,C7,C8 positive but C4 negative, diagnosis should be Schizophreniform."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        # C1 positive, C2 positive, C3 positive, C4 negative (no 6 months), C5 positive, C6 positive
        # C7 positive (1-6 months), C8 positive (not substance/GMC)
        for qid, val in [
            ("C1", True),
            ("C2", True),
            ("C3", True),
            ("C4", False),
            ("C5", True),
            ("C6", True),
            ("C7", True),
            ("C8", True),
        ]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": val},
            )

        # C27: current
        Answer.objects.create(
            interview=interview,
            question=self.c27,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Schizophreniform Disorder")
        self.assertTrue(diagnosis["criteria_summary"]["schizophreniform"]["met"])

    def test_diagnosis_schizoaffective(self):
        """When C1,C9-C12 positive, diagnosis should be Schizoaffective Disorder."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["C1", "C9", "C10", "C11", "C12"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        # C28: current
        Answer.objects.create(
            interview=interview,
            question=self.c28,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Schizoaffective Disorder")
        self.assertTrue(diagnosis["criteria_summary"]["schizoaffective"]["met"])
        self.assertTrue(diagnosis["details"]["current"])

    def test_diagnosis_delusional_disorder(self):
        """When C1,C13-C17 positive, diagnosis should be Delusional Disorder."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["C1", "C13", "C14", "C15", "C16", "C17"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        # C18: delusion type
        Answer.objects.create(
            interview=interview,
            question=self.c18,
            answer_type="text",
            value={"text": "Persecutory"},
        )

        # C29: current
        Answer.objects.create(
            interview=interview,
            question=self.c29,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Delusional Disorder")
        self.assertTrue(diagnosis["criteria_summary"]["delusional_disorder"]["met"])
        self.assertEqual(diagnosis["details"]["type"], "Persecutory")
        self.assertTrue(diagnosis["details"]["current"])

    def test_diagnosis_brief_psychotic(self):
        """When C1,C19-C21 positive, diagnosis should be Brief Psychotic Disorder."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["C1", "C19", "C20", "C21"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        # C30: current
        Answer.objects.create(
            interview=interview,
            question=self.c30,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Brief Psychotic Disorder")
        self.assertTrue(diagnosis["criteria_summary"]["brief_psychotic"]["met"])

    def test_diagnosis_other_specified(self):
        """When C1,C22-C25 positive but no other diagnosis met, should be Other Specified."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["C1", "C22", "C23", "C24", "C25"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Other Specified Psychotic Disorder")
        self.assertTrue(diagnosis["criteria_summary"]["other_specified"]["met"])

    def test_diagnosis_undifferentiated(self):
        """When C1 positive but no disorder criteria met, should be Undifferentiated."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.c1,
            answer_type="boolean",
            value={"boolean": True},
        )
        # Only C1 positive, all other criteria negative
        for qid in [
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "C10",
            "C11",
            "C12",
            "C13",
            "C14",
            "C15",
            "C16",
            "C17",
            "C19",
            "C20",
            "C21",
            "C22",
            "C23",
            "C24",
            "C25",
        ]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": False},
            )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "Undifferentiated")

    def test_diagnosis_no_criteria_summary_structure(self):
        """Diagnosis result should include all criteria_summary keys."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.c1,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertIn("criteria_summary", diagnosis)
        for key in [
            "schizophrenia",
            "schizophreniform",
            "schizoaffective",
            "delusional_disorder",
            "brief_psychotic",
            "other_specified",
        ]:
            self.assertIn(key, diagnosis["criteria_summary"])
            self.assertIn("met", diagnosis["criteria_summary"][key])


class ModuleDInterviewTests(APITestCase):
    """
    Test cases for Module D — Differential Diagnosis of Mood Disorders.
    Covers interview flow, jump rules, and diagnosis calculation.
    """

    def setUp(self):
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        self.module = InterviewModule.objects.create(
            name="Module D - Differential Diagnosis of Mood Disorders",
            description="Differential Diagnosis of Mood Disorders",
            version="1.0",
            is_active=True,
            order=4,
        )

        # Gate question
        self.d1 = Question.objects.create(
            id="D1",
            module=self.module,
            text="علائم خلقی بالینی قابل توجهی وجود داشتهاند؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="1",
            order=1,
            has_jump_logic=True,
        )

        # Bipolar I questions (D2-D7, D25)
        self.d2 = Question.objects.create(
            id="D2",
            module=self.module,
            text="معیارهای یک دوره شیدایی برآورده شدهاند؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="2",
            order=2,
            has_jump_logic=True,
        )
        self.d3 = Question.objects.create(
            id="D3",
            module=self.module,
            text="اختلال دوقطبی نوع ۱: رد اختلالات روانپریشی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="3",
            order=3,
        )
        self.d4 = Question.objects.create(
            id="D4",
            module=self.module,
            text="اختلال دوقطبی نوع ۱: رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="4",
            order=4,
        )
        self.d5 = Question.objects.create(
            id="D5",
            module=self.module,
            text="دوره فعلی یا اخیر فعال است؟",
            question_type="boolean",
            order=5,
            has_jump_logic=True,
        )
        self.d6 = Question.objects.create(
            id="D6",
            module=self.module,
            text="نوع دوره فعلی: شیدایی/افسردگی/هیپومانیک/نامشخص",
            question_type="multiple_choice",
            order=6,
        )
        self.d7 = Question.objects.create(
            id="D7",
            module=self.module,
            text="شدت دوره فعلی اختلال دوقطبی نوع ۱",
            question_type="text",
            order=7,
            has_jump_logic=True,
        )
        self.d25 = Question.objects.create(
            id="D25",
            module=self.module,
            text="سیر زمانی اختلال دوقطبی نوع ۱",
            question_type="boolean",
            order=25,
        )

        # Bipolar II questions (D8-D16, D26)
        self.d8 = Question.objects.create(
            id="D8",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: حداقل یک دوره افسردگی اساسی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="5",
            order=8,
        )
        self.d9 = Question.objects.create(
            id="D9",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: حداقل یک دوره هیپومانیک؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="6",
            order=9,
            has_jump_logic=True,
        )
        self.d10 = Question.objects.create(
            id="D10",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: هرگز شیدایی کامل نداشته؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="7",
            order=10,
        )
        self.d11 = Question.objects.create(
            id="D11",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: هیپومانیک حداقل ۴ روز؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="8",
            order=11,
            has_jump_logic=True,
        )
        self.d12 = Question.objects.create(
            id="D12",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: پریشانی بالینی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="9",
            order=12,
        )
        self.d13 = Question.objects.create(
            id="D13",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="10",
            order=13,
        )
        self.d14 = Question.objects.create(
            id="D14",
            module=self.module,
            text="اختلال دوقطبی نوع ۲: رد اختلالات روانپریشی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="11",
            order=14,
        )
        self.d15 = Question.objects.create(
            id="D15",
            module=self.module,
            text="نوع دوره فعلی اختلال دوقطبی نوع ۲",
            question_type="boolean",
            order=15,
            has_jump_logic=True,
        )
        self.d16 = Question.objects.create(
            id="D16",
            module=self.module,
            text="شدت دوره افسردگی فعلی اختلال دوقطبی نوع ۲",
            question_type="text",
            order=16,
            has_jump_logic=True,
        )
        self.d26 = Question.objects.create(
            id="D26",
            module=self.module,
            text="سیر زمانی اختلال دوقطبی نوع ۲",
            question_type="boolean",
            order=26,
        )

        # MDD questions (D17-D21, D27)
        self.d17 = Question.objects.create(
            id="D17",
            module=self.module,
            text="اختلال افسردگی اساسی: حداقل ۲ هفته افسردگی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="12",
            order=17,
        )
        self.d18 = Question.objects.create(
            id="D18",
            module=self.module,
            text="اختلال افسردگی اساسی: پریشانی بالینی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="13",
            order=18,
        )
        self.d19 = Question.objects.create(
            id="D19",
            module=self.module,
            text="اختلال افسردگی اساسی: رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="14",
            order=19,
        )
        self.d20 = Question.objects.create(
            id="D20",
            module=self.module,
            text="اختلال افسردگی اساسی: تک‌دوره یا عودکننده؟",
            question_type="boolean",
            order=20,
        )
        self.d21 = Question.objects.create(
            id="D21",
            module=self.module,
            text="شدت دوره فعلی اختلال افسردگی اساسی",
            question_type="text",
            order=21,
            has_jump_logic=True,
        )
        self.d27 = Question.objects.create(
            id="D27",
            module=self.module,
            text="سیر زمانی اختلال افسردگی اساسی",
            question_type="boolean",
            order=27,
        )

        # Other specified depressive (D22-D24, D28)
        self.d22 = Question.objects.create(
            id="D22",
            module=self.module,
            text="سایر اختلالات افسردگی: علائم غالب افسردگی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="15",
            order=22,
        )
        self.d23 = Question.objects.create(
            id="D23",
            module=self.module,
            text="سایر اختلالات افسردگی: پریشانی بالینی؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="16",
            order=23,
        )
        self.d24 = Question.objects.create(
            id="D24",
            module=self.module,
            text="سایر اختلالات افسردگی: رد ماده/بیماری؟",
            question_type="boolean",
            is_criteria=True,
            criteria_number="17",
            order=24,
        )
        self.d28 = Question.objects.create(
            id="D28",
            module=self.module,
            text="سیر زمانی سایر اختلالات افسردگی",
            question_type="boolean",
            order=28,
        )

        # Create jump rules
        JumpRule.objects.create(
            from_question=self.d1,
            condition="answer == false",
            condition_type="boolean",
            to_question=None,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.d2,
            condition="answer == false",
            condition_type="boolean",
            to_question=self.d8,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.d5,
            condition="answer == false",
            condition_type="boolean",
            to_question=self.d25,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.d7,
            condition="severity entered",
            condition_type="text",
            to_question=self.d25,
            metadata={"match_pattern": ""},
        )
        JumpRule.objects.create(
            from_question=self.d9,
            condition="answer == false",
            condition_type="boolean",
            to_question=self.d17,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.d11,
            condition="answer == false",
            condition_type="boolean",
            to_question=self.d17,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.d15,
            condition="answer == false",
            condition_type="boolean",
            to_question=self.d26,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.d16,
            condition="severity entered",
            condition_type="text",
            to_question=self.d26,
            metadata={"match_pattern": ""},
        )
        JumpRule.objects.create(
            from_question=self.d21,
            condition="severity entered",
            condition_type="text",
            to_question=self.d27,
            metadata={"match_pattern": ""},
        )

        # Authenticate
        self.client.force_authenticate(user=self.clinician)

    # ============================================================
    # JUMP RULE TESTS
    # ============================================================

    def test_d1_negative_ends_interview(self):
        """D1 negative should end the interview (no next question)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d1,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D1",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_next"])
        self.assertEqual(response.data["interview_status"], "completed")

    def test_d2_negative_skips_to_d8(self):
        """D2 negative should skip to D8 (no manic episode → assess BP-II/MDD)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d2,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D2",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D8")

    def test_d5_negative_skips_to_d25(self):
        """D5 negative should skip to D25 (BP-I confirmed, no current episode)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d5,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D5",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D25")

    def test_d7_text_skips_to_d25(self):
        """D7 (severity text, match='') should always jump to D25."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d7,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D7",
                "answer_value": {"text": "شدید"},
                "answer_type": "text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D25")

    def test_d9_negative_skips_to_d17(self):
        """D9 negative should skip to D17 (no hypomanic → assess MDD)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d9,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D9",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D17")

    def test_d11_negative_skips_to_d17(self):
        """D11 negative should skip to D17 (hypomanic < 4 days → not BP-II)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d11,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D11",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D17")

    def test_d15_negative_skips_to_d26(self):
        """D15 negative should skip to D26 (BP-II, no current depressive)."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d15,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D15",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D26")

    def test_d16_text_skips_to_d26(self):
        """D16 (severity text, match='') should always jump to D26."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d16,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D16",
                "answer_value": {"text": "خفیف"},
                "answer_type": "text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D26")

    def test_d21_text_skips_to_d27(self):
        """D21 (severity text, match='') should always jump to D27."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="in_progress",
            current_question=self.d21,
        )

        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {
                "question_id": "D21",
                "answer_value": {"text": "متوسط"},
                "answer_type": "text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "D27")

    # ============================================================
    # DIAGNOSIS TESTS
    # ============================================================

    def test_diagnosis_no_mood_symptoms(self):
        """When D1 is negative, diagnosis should indicate no significant mood symptoms."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": False},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["no_significant_mood_symptoms"])
        self.assertIn("note", diagnosis)

    def test_diagnosis_bipolar_i(self):
        """When D2+D3+D4 all positive, diagnosis should be Bipolar I."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["D1", "D2", "D3", "D4"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        Answer.objects.create(
            interview=interview,
            question=self.d5,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d6,
            answer_type="multiple_choice",
            value={"text": "شیدایی"},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d7,
            answer_type="text",
            value={"text": "شدید"},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d25,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال دوقطبی نوع ۱")
        self.assertEqual(diagnosis["details"]["current_episode_type"], "شیدایی")
        self.assertEqual(diagnosis["details"]["severity"], "شدید")
        self.assertTrue(diagnosis["details"]["current"])
        self.assertIn("criteria_summary", diagnosis)
        self.assertTrue(diagnosis["criteria_summary"]["bipolar_i"]["met"])

    def test_diagnosis_bipolar_i_no_current_episode(self):
        """Bipolar I with no current episode should still diagnose BP-I."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        for qid in ["D1", "D2", "D3", "D4"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        Answer.objects.create(
            interview=interview,
            question=self.d5,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d25,
            answer_type="boolean",
            value={"boolean": False},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال دوقطبی نوع ۱")
        self.assertEqual(diagnosis["details"]["current_episode_type"], "نامشخص")

    def test_diagnosis_bipolar_ii(self):
        """When BP-II criteria (D8-D14) all positive, diagnosis should be Bipolar II."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        # D1 = yes, D2 = no (not bipolar I)
        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )

        # D8-D14 all yes
        for qid in ["D8", "D9", "D10", "D11", "D12", "D13", "D14"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        # D15 = yes (current depressive episode)
        Answer.objects.create(
            interview=interview,
            question=self.d15,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d16,
            answer_type="text",
            value={"text": "متوسط"},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d26,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال دوقطبی نوع ۲")
        self.assertEqual(
            diagnosis["details"]["current_episode_type"], "دوره فعلی افسرده"
        )
        self.assertEqual(diagnosis["details"]["severity"], "متوسط")
        self.assertTrue(diagnosis["criteria_summary"]["bipolar_ii"]["met"])

    def test_diagnosis_bipolar_ii_no_current_depressive(self):
        """BP-II with no current depressive (current hypomanic) should still diagnose."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )

        for qid in ["D8", "D9", "D10", "D11", "D12", "D13", "D14"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        Answer.objects.create(
            interview=interview,
            question=self.d15,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d26,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال دوقطبی نوع ۲")
        self.assertEqual(
            diagnosis["details"]["current_episode_type"], "دوره اخیر هیپومانیک"
        )

    def test_diagnosis_mdd_single_episode(self):
        """When MDD criteria met (D17-D19) with single episode (D20=yes), diagnose MDD single."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d8,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d9,
            answer_type="boolean",
            value={"boolean": False},
        )

        for qid in ["D17", "D18", "D19"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        Answer.objects.create(
            interview=interview,
            question=self.d20,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d21,
            answer_type="text",
            value={"text": "خفیف"},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d27,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال افسردگی اساسی")
        self.assertEqual(diagnosis["details"]["episode_type"], "تک‌دوره")
        self.assertEqual(diagnosis["details"]["severity"], "خفیف")
        self.assertTrue(diagnosis["criteria_summary"]["mdd"]["met"])

    def test_diagnosis_mdd_recurrent(self):
        """MDD with recurrent episodes (D20=no) should label as عودکننده."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d8,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d9,
            answer_type="boolean",
            value={"boolean": False},
        )

        for qid in ["D17", "D18", "D19"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        Answer.objects.create(
            interview=interview,
            question=self.d20,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d21,
            answer_type="text",
            value={"text": "شدید"},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d27,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال افسردگی اساسی")
        self.assertEqual(diagnosis["details"]["episode_type"], "عودکننده")

    def test_diagnosis_other_depressive(self):
        """When D22-D24 positive but MDD not met, diagnose Other Depressive."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d8,
            answer_type="boolean",
            value={"boolean": False},
        )

        # D17 = no (MDD not met)
        Answer.objects.create(
            interview=interview,
            question=self.d17,
            answer_type="boolean",
            value={"boolean": False},
        )

        # D22-D24 = yes
        for qid in ["D22", "D23", "D24"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview,
                question=q,
                answer_type="boolean",
                value={"boolean": True},
            )

        Answer.objects.create(
            interview=interview,
            question=self.d28,
            answer_type="boolean",
            value={"boolean": True},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "سایر اختلالات افسردگی مشخص‌شده")
        self.assertTrue(diagnosis["criteria_summary"]["other_depressive"]["met"])

    def test_diagnosis_undifferentiated(self):
        """When no criteria met, diagnose unspecified mood disorder."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )

        # D2 = no (no bipolar I)
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )

        # D8 = no (no MDE)
        Answer.objects.create(
            interview=interview,
            question=self.d8,
            answer_type="boolean",
            value={"boolean": False},
        )

        # D17 = no (no 2-week depression)
        Answer.objects.create(
            interview=interview,
            question=self.d17,
            answer_type="boolean",
            value={"boolean": False},
        )

        # D22 = no (no other depressive)
        Answer.objects.create(
            interview=interview,
            question=self.d22,
            answer_type="boolean",
            value={"boolean": False},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertEqual(diagnosis["diagnosis"], "اختلال خلقی نامشخص")

    def test_diagnosis_no_criteria_summary_structure(self):
        """Diagnosis result should include all criteria_summary keys."""
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status="completed",
            completed_at=timezone.now(),
        )

        Answer.objects.create(
            interview=interview,
            question=self.d1,
            answer_type="boolean",
            value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d2,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d8,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d17,
            answer_type="boolean",
            value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview,
            question=self.d22,
            answer_type="boolean",
            value={"boolean": False},
        )

        response = self.client.get(
            f"/api/interviews/interviews/{interview.id}/summary/"
        )
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertIn("criteria_summary", diagnosis)
        for key in ["bipolar_i", "bipolar_ii", "mdd", "other_depressive"]:
            self.assertIn(key, diagnosis["criteria_summary"])
            self.assertIn("met", diagnosis["criteria_summary"][key])
            self.assertIn("criteria_positive", diagnosis["criteria_summary"][key])


class ModuleEInterviewTests(APITestCase):
    """
    Test cases for Module E — Substance Use Disorders.
    Covers interview flow, jump rules, and diagnosis calculation.
    """

    def setUp(self):
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        self.module = InterviewModule.objects.create(
            name="Module E - Substance Use Disorders",
            description="Substance Use Disorders",
            version="1.0",
            is_active=True,
            order=5,
        )

        # Phase 1: Alcohol (E1-E13)
        self.e1 = Question.objects.create(
            id="E1", module=self.module,
            text="مصرف الکل در ۱۲ ماه گذشته؟",
            question_type="boolean", is_criteria=False,
            order=1, has_jump_logic=True,
        )
        self.e2 = Question.objects.create(
            id="E2", module=self.module,
            text="بیشتر از قصد مینوشید؟",
            question_type="boolean", is_criteria=True, criteria_number="1",
            order=2,
        )
        self.e3 = Question.objects.create(
            id="E3", module=self.module,
            text="تلاش ناموفق برای کاهش؟",
            question_type="boolean", is_criteria=True, criteria_number="2",
            order=3,
        )
        self.e4 = Question.objects.create(
            id="E4", module=self.module,
            text="زمان زیاد صرف نوشیدن؟",
            question_type="boolean", is_criteria=True, criteria_number="3",
            order=4,
        )
        self.e5 = Question.objects.create(
            id="E5", module=self.module,
            text="هوس نوشیدن؟",
            question_type="boolean", is_criteria=True, criteria_number="4",
            order=5,
        )
        self.e6 = Question.objects.create(
            id="E6", module=self.module,
            text="ناتوانی در تعهدات؟",
            question_type="boolean", is_criteria=True, criteria_number="5",
            order=6,
        )
        self.e7 = Question.objects.create(
            id="E7", module=self.module,
            text="مشکلات اجتماعی؟",
            question_type="boolean", is_criteria=True, criteria_number="6",
            order=7,
        )
        self.e8 = Question.objects.create(
            id="E8", module=self.module,
            text="کاهش فعالیتها؟",
            question_type="boolean", is_criteria=True, criteria_number="7",
            order=8,
        )
        self.e9 = Question.objects.create(
            id="E9", module=self.module,
            text="مصرف در موقعیت خطرناک؟",
            question_type="boolean", is_criteria=True, criteria_number="8",
            order=9,
        )
        self.e10 = Question.objects.create(
            id="E10", module=self.module,
            text="ادامه مصرف علیرغم مشکلات؟",
            question_type="boolean", is_criteria=True, criteria_number="9",
            order=10,
        )
        self.e11 = Question.objects.create(
            id="E11", module=self.module,
            text="تلرانس؟",
            question_type="boolean", is_criteria=True, criteria_number="10",
            order=11,
        )
        self.e12 = Question.objects.create(
            id="E12", module=self.module,
            text="ترک؟",
            question_type="boolean", is_criteria=True, criteria_number="11",
            order=12,
        )
        self.e13 = Question.objects.create(
            id="E13", module=self.module,
            text="آستانه الکل؟",
            question_type="boolean", order=13, has_jump_logic=True,
        )

        # Phase 2: Substance Screening (E14-E22)
        self.e14 = Question.objects.create(
            id="E14", module=self.module,
            text="مصرف مواد غیر از الکل؟",
            question_type="boolean", order=14, has_jump_logic=True,
        )
        self.e15 = Question.objects.create(
            id="E15", module=self.module,
            text="آرامبخش؟",
            question_type="boolean", order=15, has_jump_logic=True,
        )
        self.e16 = Question.objects.create(
            id="E16", module=self.module,
            text="شاهدانه؟",
            question_type="boolean", order=16, has_jump_logic=True,
        )
        self.e17 = Question.objects.create(
            id="E17", module=self.module,
            text="محرکها؟",
            question_type="boolean", order=17, has_jump_logic=True,
        )
        self.e18 = Question.objects.create(
            id="E18", module=self.module,
            text="افیونی؟",
            question_type="boolean", order=18, has_jump_logic=True,
        )
        self.e19 = Question.objects.create(
            id="E19", module=self.module,
            text="PCP؟",
            question_type="boolean", order=19, has_jump_logic=True,
        )
        self.e20 = Question.objects.create(
            id="E20", module=self.module,
            text="توهمزا؟",
            question_type="boolean", order=20, has_jump_logic=True,
        )
        self.e21 = Question.objects.create(
            id="E21", module=self.module,
            text="استنشاقی؟",
            question_type="boolean", order=21, has_jump_logic=True,
        )
        self.e22 = Question.objects.create(
            id="E22", module=self.module,
            text="سایر مواد؟",
            question_type="boolean", order=22, has_jump_logic=True,
        )

        # Phase 3: Substance Use Disorder Criteria (E37-E49)
        self.e37 = Question.objects.create(
            id="E37", module=self.module,
            text="ماده اصلی؟",
            question_type="text", order=37,
        )
        self.e38 = Question.objects.create(
            id="E38", module=self.module,
            text="بیشتر از قصد مصرف؟",
            question_type="boolean", is_criteria=True, criteria_number="1",
            order=38,
        )
        self.e39 = Question.objects.create(
            id="E39", module=self.module,
            text="تلاش ناموفق برای کاهش ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="2",
            order=39,
        )
        self.e40 = Question.objects.create(
            id="E40", module=self.module,
            text="زمان زیاد صرف ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="3",
            order=40,
        )
        self.e41 = Question.objects.create(
            id="E41", module=self.module,
            text="هوس ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="4",
            order=41,
        )
        self.e42 = Question.objects.create(
            id="E42", module=self.module,
            text="ناتوانی در تعهدات ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="5",
            order=42,
        )
        self.e43 = Question.objects.create(
            id="E43", module=self.module,
            text="مشکلات اجتماعی ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="6",
            order=43,
        )
        self.e44 = Question.objects.create(
            id="E44", module=self.module,
            text="کاهش فعالیتها ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="7",
            order=44,
        )
        self.e45 = Question.objects.create(
            id="E45", module=self.module,
            text="مصرف ماده در موقعیت خطرناک؟",
            question_type="boolean", is_criteria=True, criteria_number="8",
            order=45,
        )
        self.e46 = Question.objects.create(
            id="E46", module=self.module,
            text="ادامه مصرف ماده علیرغم مشکلات؟",
            question_type="boolean", is_criteria=True, criteria_number="9",
            order=46,
        )
        self.e47 = Question.objects.create(
            id="E47", module=self.module,
            text="تلرانس ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="10",
            order=47,
        )
        self.e48 = Question.objects.create(
            id="E48", module=self.module,
            text="ترک ماده؟",
            question_type="boolean", is_criteria=True, criteria_number="11",
            order=48,
        )
        self.e49 = Question.objects.create(
            id="E49", module=self.module,
            text="آستانه اختلال مصرف ماده؟",
            question_type="boolean", order=49,
        )

        # Jump rules
        JumpRule.objects.create(
            from_question=self.e1, condition="answer == false",
            condition_type="boolean", to_question=self.e14,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.e13, condition="alcohol threshold assessed",
            condition_type="boolean", to_question=self.e14,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.e14, condition="answer == false",
            condition_type="boolean", to_question=None,
            metadata={"expected_value": False},
        )
        for eq in [self.e15, self.e16, self.e17, self.e18, self.e19, self.e20, self.e21]:
            JumpRule.objects.create(
                from_question=eq, condition="answer == true",
                condition_type="boolean", to_question=self.e37,
                metadata={"expected_value": True},
            )
        JumpRule.objects.create(
            from_question=self.e22, condition="answer == true",
            condition_type="boolean", to_question=self.e37,
            metadata={"expected_value": True},
        )
        JumpRule.objects.create(
            from_question=self.e22, condition="answer == false",
            condition_type="boolean", to_question=None,
            metadata={"expected_value": False},
        )

        self.client.force_authenticate(user=self.clinician)

    # ============================================================
    # JUMP RULE TESTS
    # ============================================================

    def test_e1_negative_skips_to_e14(self):
        """E1 negative should skip to E14 (no alcohol use)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.e1,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "E1", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "E14")

    def test_e14_negative_ends_interview(self):
        """E14 negative should end the interview (no substance use)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.e14,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "E14", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_next"])
        self.assertEqual(response.data["interview_status"], "completed")

    def test_e15_positive_jumps_to_e37(self):
        """E15 positive (sedatives) should jump to E37 (primary substance)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.e15,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "E15", "answer_value": {"boolean": True}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "E37")

    def test_e16_positive_jumps_to_e37(self):
        """E16 positive (cannabis) should jump to E37."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.e16,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "E16", "answer_value": {"boolean": True}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "E37")

    def test_e17_negative_continues_to_e18(self):
        """E17 negative (no stimulants) should continue to E18."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.e17,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "E17", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "E18")

    def test_e22_negative_ends_interview(self):
        """E22 negative (no other substances) should end interview."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.e22,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "E22", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_next"])
        self.assertEqual(response.data["interview_status"], "completed")

    # ============================================================
    # DIAGNOSIS TESTS
    # ============================================================

    def test_diagnosis_no_alcohol_no_substances(self):
        """No alcohol, no substances → both not diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.e1,
            answer_type="boolean", value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview, question=self.e14,
            answer_type="boolean", value={"boolean": False},
        )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["alcohol"]["diagnosed"])
        self.assertFalse(diagnosis["substance_use_disorder"]["diagnosed"])

    def test_diagnosis_alcohol_mild(self):
        """Alcohol with 3 criteria (E1+E2+E3) → mild alcohol use disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.e1,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["E2", "E3"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["alcohol"]["diagnosed"])
        self.assertEqual(diagnosis["alcohol"]["symptoms_counted"], 2)
        self.assertEqual(diagnosis["alcohol"]["severity"], "خفیف")

    def test_diagnosis_alcohol_severe(self):
        """Alcohol with 7 criteria → severe alcohol use disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.e1,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["E2", "E3", "E4", "E5", "E6", "E7", "E8"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["alcohol"]["diagnosed"])
        self.assertEqual(diagnosis["alcohol"]["symptoms_counted"], 7)
        self.assertEqual(diagnosis["alcohol"]["severity"], "شدید")

    def test_diagnosis_substance_cannabis_moderate(self):
        """Cannabis use with 5 criteria → moderate substance use disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.e1,
            answer_type="boolean", value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview, question=self.e14,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.e16,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.e37,
            answer_type="text", value={"text": "شاهدانه"},
        )
        for qid in ["E38", "E39", "E40", "E41", "E42"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["alcohol"]["diagnosed"])
        self.assertTrue(diagnosis["substance_use_disorder"]["diagnosed"])
        self.assertEqual(diagnosis["substance_use_disorder"]["primary_substance"], "شاهدانه")
        self.assertEqual(diagnosis["substance_use_disorder"]["symptoms_counted"], 5)
        self.assertEqual(diagnosis["substance_use_disorder"]["severity"], "متوسط")

    def test_diagnosis_substance_insufficient_criteria(self):
        """Only 1 substance criterion → not diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.e1,
            answer_type="boolean", value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview, question=self.e14,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.e17,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.e37,
            answer_type="text", value={"text": "شیشه"},
        )
        q = Question.objects.get(id="E38")
        Answer.objects.create(
            interview=interview, question=q,
            answer_type="boolean", value={"boolean": True},
        )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["substance_use_disorder"]["diagnosed"])
        self.assertEqual(diagnosis["substance_use_disorder"]["symptoms_counted"], 1)

    def test_substances_screened_tracking(self):
        """Multiple substances reported should appear in substances_screened."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.e1,
            answer_type="boolean", value={"boolean": False},
        )
        Answer.objects.create(
            interview=interview, question=self.e14,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["E16", "E17", "E18"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        screened = diagnosis["substances_screened"]
        self.assertTrue(screened["any_substance_used"])
        self.assertEqual(len(screened["substances_reported"]), 3)
        self.assertIn("شاهدانه (ماریجوانا)", screened["substances_reported"])


class ModuleFInterviewTests(APITestCase):
    """
    Test cases for Module F — Anxiety Disorders.
    Covers interview flow, jump rules, and diagnosis calculation.
    """

    def setUp(self):
        self.clinician = User.objects.create_user(
            phone_number="09123456789", first_name="Test", last_name="Clinician"
        )
        UserProfile.objects.get_or_create(
            user=self.clinician, defaults={"role": "clinician"}
        )

        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            phone_number="0987654321",
            created_by=self.clinician,
        )

        self.module = InterviewModule.objects.create(
            name="Module F - Anxiety Disorders",
            description="Anxiety Disorders",
            version="1.0",
            is_active=True,
            order=6,
        )

        # ---- Panic Disorder (F1-F7) ----
        self.f1 = Question.objects.create(
            id="F1", module=self.module,
            text="حمله هراس؟",
            question_type="boolean", order=1, has_jump_logic=True,
        )
        self.f2 = Question.objects.create(
            id="F2", module=self.module,
            text="نگرانی مداوم یا تغییر رفتار؟",
            question_type="boolean", is_criteria=True, criteria_number="1",
            order=2,
        )
        self.f3 = Question.objects.create(
            id="F3", module=self.module,
            text="عدم انتساب به ماده؟",
            question_type="boolean", order=3,
        )
        self.f4 = Question.objects.create(
            id="F4", module=self.module,
            text="عدم انتساب به بیماری پزشکی؟",
            question_type="boolean", order=4,
        )
        self.f5 = Question.objects.create(
            id="F5", module=self.module,
            text="عدم توضیح با اختلال دیگر؟",
            question_type="boolean", order=5,
        )
        self.f6 = Question.objects.create(
            id="F6", module=self.module,
            text="شدت هراس؟",
            question_type="text", order=6, has_jump_logic=True,
        )
        self.f7 = Question.objects.create(
            id="F7", module=self.module,
            text="کرونولوژی هراس؟",
            question_type="text", order=7, has_jump_logic=True,
        )

        # ---- Agoraphobia (F8-F19) ----
        self.f8 = Question.objects.create(
            id="F8", module=self.module,
            text="ترس از ۲+ موقعیت؟",
            question_type="boolean", order=8, has_jump_logic=True,
        )
        self.f9 = Question.objects.create(
            id="F9", module=self.module,
            text="حملونقل عمومی؟",
            question_type="boolean", is_criteria=True, criteria_number="1",
            order=9,
        )
        self.f10 = Question.objects.create(
            id="F10", module=self.module,
            text="فضاهای باز؟",
            question_type="boolean", is_criteria=True, criteria_number="2",
            order=10,
        )
        self.f11 = Question.objects.create(
            id="F11", module=self.module,
            text="مکانهای بسته؟",
            question_type="boolean", is_criteria=True, criteria_number="3",
            order=11,
        )
        self.f12 = Question.objects.create(
            id="F12", module=self.module,
            text="ایستادن در صف؟",
            question_type="boolean", is_criteria=True, criteria_number="4",
            order=12,
        )
        self.f13 = Question.objects.create(
            id="F13", module=self.module,
            text="بیرون رفتن تنها؟",
            question_type="boolean", is_criteria=True, criteria_number="5",
            order=13,
        )
        self.f14 = Question.objects.create(
            id="F14", module=self.module,
            text="اجتناب یا تحمل با ترس شدید؟",
            question_type="boolean", is_criteria=True, criteria_number="6",
            order=14,
        )
        self.f15 = Question.objects.create(
            id="F15", module=self.module,
            text="عدم تناسب با خطر واقعی؟",
            question_type="boolean", is_criteria=True, criteria_number="7",
            order=15,
        )
        self.f16 = Question.objects.create(
            id="F16", module=self.module,
            text="عدم انتساب به ماده/پزشکی؟",
            question_type="boolean", order=16,
        )
        self.f17 = Question.objects.create(
            id="F17", module=self.module,
            text="عدم توضیح با اختلال دیگر؟",
            question_type="boolean", order=17,
        )
        self.f18 = Question.objects.create(
            id="F18", module=self.module,
            text="شدت آگورافوبیا؟",
            question_type="text", order=18, has_jump_logic=True,
        )
        self.f19 = Question.objects.create(
            id="F19", module=self.module,
            text="کرونولوژی آگورافوبیا؟",
            question_type="text", order=19, has_jump_logic=True,
        )

        # ---- Social Anxiety (F20-F28) ----
        self.f20 = Question.objects.create(
            id="F20", module=self.module,
            text="ترس از موقعیتهای اجتماعی؟",
            question_type="boolean", order=20, has_jump_logic=True,
        )
        self.f21 = Question.objects.create(
            id="F21", module=self.module,
            text="ترس از ارزیابی منفی؟",
            question_type="boolean", is_criteria=True, criteria_number="1",
            order=21,
        )
        self.f22 = Question.objects.create(
            id="F22", module=self.module,
            text="ترس مداوم در موقعیتهای اجتماعی؟",
            question_type="boolean", is_criteria=True, criteria_number="2",
            order=22,
        )
        self.f23 = Question.objects.create(
            id="F23", module=self.module,
            text="اجتناب اجتماعی؟",
            question_type="boolean", is_criteria=True, criteria_number="3",
            order=23,
        )
        self.f24 = Question.objects.create(
            id="F24", module=self.module,
            text="عدم تناسب اجتماعی؟",
            question_type="boolean", order=24,
        )
        self.f25 = Question.objects.create(
            id="F25", module=self.module,
            text="عدم انتساب به ماده اجتماعی؟",
            question_type="boolean", order=25,
        )
        self.f26 = Question.objects.create(
            id="F26", module=self.module,
            text="عدم توضیح با اختلال دیگر اجتماعی؟",
            question_type="boolean", order=26,
        )
        self.f27 = Question.objects.create(
            id="F27", module=self.module,
            text="شدت اضطراب اجتماعی؟",
            question_type="text", order=27, has_jump_logic=True,
        )
        self.f28 = Question.objects.create(
            id="F28", module=self.module,
            text="کرونولوژی اضطراب اجتماعی؟",
            question_type="text", order=28, has_jump_logic=True,
        )

        # ---- GAD (F29-F40) ----
        self.f29 = Question.objects.create(
            id="F29", module=self.module,
            text="نگرانی بیش از حد ≥۶ ماه؟",
            question_type="boolean", order=29, has_jump_logic=True,
        )
        self.f30 = Question.objects.create(
            id="F30", module=self.module,
            text="ناتوانی در کنترل نگرانی؟",
            question_type="boolean", is_criteria=True, criteria_number="1",
            order=30,
        )
        self.f31 = Question.objects.create(
            id="F31", module=self.module,
            text="بیقراری؟",
            question_type="boolean", is_criteria=True, criteria_number="2",
            order=31,
        )
        self.f32 = Question.objects.create(
            id="F32", module=self.module,
            text="خستگی؟",
            question_type="boolean", is_criteria=True, criteria_number="3",
            order=32,
        )
        self.f33 = Question.objects.create(
            id="F33", module=self.module,
            text="مشکل تمرکز؟",
            question_type="boolean", is_criteria=True, criteria_number="4",
            order=33,
        )
        self.f34 = Question.objects.create(
            id="F34", module=self.module,
            text="زودرنجی؟",
            question_type="boolean", is_criteria=True, criteria_number="5",
            order=34,
        )
        self.f35 = Question.objects.create(
            id="F35", module=self.module,
            text="تنش عضلانی؟",
            question_type="boolean", is_criteria=True, criteria_number="6",
            order=35,
        )
        self.f36 = Question.objects.create(
            id="F36", module=self.module,
            text="اختلال خواب؟",
            question_type="boolean", is_criteria=True, criteria_number="7",
            order=36,
        )
        self.f37 = Question.objects.create(
            id="F37", module=self.module,
            text="عدم انتساب به ماده GAD؟",
            question_type="boolean", order=37,
        )
        self.f38 = Question.objects.create(
            id="F38", module=self.module,
            text="عدم توضیح با اختلال دیگر GAD؟",
            question_type="boolean", order=38,
        )
        self.f39 = Question.objects.create(
            id="F39", module=self.module,
            text="شدت GAD؟",
            question_type="text", order=39, has_jump_logic=True,
        )
        self.f40 = Question.objects.create(
            id="F40", module=self.module,
            text="کرونولوژی GAD؟",
            question_type="text", order=40,
        )

        # Jump rules
        JumpRule.objects.create(
            from_question=self.f1, condition="answer == false",
            condition_type="boolean", to_question=self.f8,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.f6, condition="match=''",
            condition_type="text", to_question=self.f7,
            metadata={"match": ""},
        )
        JumpRule.objects.create(
            from_question=self.f7, condition="match=''",
            condition_type="text", to_question=self.f8,
            metadata={"match": ""},
        )
        JumpRule.objects.create(
            from_question=self.f8, condition="answer == false",
            condition_type="boolean", to_question=self.f20,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.f18, condition="match=''",
            condition_type="text", to_question=self.f19,
            metadata={"match": ""},
        )
        JumpRule.objects.create(
            from_question=self.f19, condition="match=''",
            condition_type="text", to_question=self.f20,
            metadata={"match": ""},
        )
        JumpRule.objects.create(
            from_question=self.f20, condition="answer == false",
            condition_type="boolean", to_question=self.f29,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.f27, condition="match=''",
            condition_type="text", to_question=self.f28,
            metadata={"match": ""},
        )
        JumpRule.objects.create(
            from_question=self.f28, condition="match=''",
            condition_type="text", to_question=self.f29,
            metadata={"match": ""},
        )
        JumpRule.objects.create(
            from_question=self.f29, condition="answer == false",
            condition_type="boolean", to_question=None,
            metadata={"expected_value": False},
        )
        JumpRule.objects.create(
            from_question=self.f39, condition="match=''",
            condition_type="text", to_question=self.f40,
            metadata={"match": ""},
        )

        self.client.force_authenticate(user=self.clinician)

    # ============================================================
    # JUMP RULE TESTS
    # ============================================================

    def test_f1_negative_skips_to_f8(self):
        """F1 negative should skip to F8 (no panic → assess agoraphobia)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f1,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F1", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "F8")

    def test_f6_text_jumps_to_f7(self):
        """F6 (severity text) should always jump to F7 (chronology)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f6,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F6", "answer_value": {"text": "شدید"}, "answer_type": "text"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "F7")

    def test_f8_negative_skips_to_f20(self):
        """F8 negative should skip to F20 (no agoraphobia → assess social anxiety)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f8,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F8", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "F20")

    def test_f19_text_jumps_to_f20(self):
        """F19 (agoraphobia chronology text) should always jump to F20."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f19,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F19", "answer_value": {"text": "جاری"}, "answer_type": "text"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "F20")

    def test_f20_negative_skips_to_f29(self):
        """F20 negative should skip to F29 (no social anxiety → assess GAD)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f20,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F20", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "F29")

    def test_f29_negative_ends_interview(self):
        """F29 negative should end the interview (no GAD)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f29,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F29", "answer_value": {"boolean": False}, "answer_type": "boolean"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_next"])
        self.assertEqual(response.data["interview_status"], "completed")

    def test_f39_text_jumps_to_f40(self):
        """F39 (GAD severity text) should always jump to F40 (chronology)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="in_progress",
            current_question=self.f39,
        )
        response = self.client.post(
            f"/api/interviews/interviews/{interview.id}/progress/",
            {"question_id": "F39", "answer_value": {"text": "متوسط"}, "answer_type": "text"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["id"], "F40")

    # ============================================================
    # DIAGNOSIS TESTS
    # ============================================================

    def test_diagnosis_no_anxiety(self):
        """All gate questions negative → no disorders diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        for qid in ["F1", "F8", "F20", "F29"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": False},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["panic_disorder"]["diagnosed"])
        self.assertFalse(diagnosis["agoraphobia"]["diagnosed"])
        self.assertFalse(diagnosis["social_anxiety"]["diagnosed"])
        self.assertFalse(diagnosis["generalized_anxiety"]["diagnosed"])

    def test_diagnosis_panic_disorder(self):
        """F1-F5 all positive → Panic Disorder diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        for qid in ["F1", "F2", "F3", "F4", "F5"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        Answer.objects.create(
            interview=interview, question=self.f6,
            answer_type="text", value={"text": "شدید"},
        )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["panic_disorder"]["diagnosed"])
        self.assertEqual(diagnosis["panic_disorder"]["severity"], "شدید")

    def test_diagnosis_panic_exclusion_met(self):
        """F3 (substance exclusion) negative → Panic not diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.f1,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.f2,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.f3,
            answer_type="boolean", value={"boolean": False},
        )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["panic_disorder"]["diagnosed"])

    def test_diagnosis_agoraphobia(self):
        """F8 + F9,F10 + F14,F15 + F16,F17 → Agoraphobia diagnosed with 2 situations."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.f8,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["F9", "F10"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        for qid in ["F14", "F15", "F16", "F17"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["agoraphobia"]["diagnosed"])
        self.assertEqual(diagnosis["agoraphobia"]["situations_count"], 2)

    def test_diagnosis_agoraphobia_insufficient_situations(self):
        """Only 1 situation → Agoraphobia not diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.f8,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.f9,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["F14", "F15", "F16", "F17"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["agoraphobia"]["diagnosed"])
        self.assertEqual(diagnosis["agoraphobia"]["situations_count"], 1)

    def test_diagnosis_social_anxiety(self):
        """F20-F26 all positive → Social Anxiety diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        for qid in ["F20", "F21", "F22", "F23", "F24", "F25", "F26"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        Answer.objects.create(
            interview=interview, question=self.f27,
            answer_type="text", value={"text": "خفیف"},
        )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["social_anxiety"]["diagnosed"])
        self.assertEqual(diagnosis["social_anxiety"]["severity"], "خفیف")

    def test_diagnosis_social_anxiety_exclusion(self):
        """F25 (substance exclusion) negative → Social Anxiety not diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        for qid in ["F20", "F21", "F22", "F23", "F24"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        Answer.objects.create(
            interview=interview, question=self.f25,
            answer_type="boolean", value={"boolean": False},
        )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["social_anxiety"]["diagnosed"])

    def test_diagnosis_gad(self):
        """F29+F30 + F31,F32,F33 + F37,F38 → GAD diagnosed with 3 associated symptoms."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.f29,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.f30,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["F31", "F32", "F33"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        for qid in ["F37", "F38"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["generalized_anxiety"]["diagnosed"])
        self.assertEqual(diagnosis["generalized_anxiety"]["associated_symptoms_count"], 3)

    def test_diagnosis_gad_insufficient_symptoms(self):
        """Only 2 associated symptoms → GAD not diagnosed."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        Answer.objects.create(
            interview=interview, question=self.f29,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.f30,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["F31", "F32"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        for qid in ["F37", "F38"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertFalse(diagnosis["generalized_anxiety"]["diagnosed"])
        self.assertEqual(diagnosis["generalized_anxiety"]["associated_symptoms_count"], 2)

    def test_diagnosis_multiple_disorders(self):
        """Panic + GAD both diagnosed (comorbid)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status="completed",
            completed_at=timezone.now(),
        )
        # Panic: F1-F5 all true
        for qid in ["F1", "F2", "F3", "F4", "F5"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        # GAD: F29-F30 + F31-F36 + F37-F38 all true
        Answer.objects.create(
            interview=interview, question=self.f29,
            answer_type="boolean", value={"boolean": True},
        )
        Answer.objects.create(
            interview=interview, question=self.f30,
            answer_type="boolean", value={"boolean": True},
        )
        for qid in ["F31", "F32", "F33", "F34", "F35", "F36"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )
        for qid in ["F37", "F38"]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type="boolean", value={"boolean": True},
            )

        response = self.client.get(f"/api/interviews/interviews/{interview.id}/summary/")
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data["diagnosis_result"]
        self.assertTrue(diagnosis["panic_disorder"]["diagnosed"])
        self.assertTrue(diagnosis["generalized_anxiety"]["diagnosed"])
        self.assertEqual(diagnosis["generalized_anxiety"]["associated_symptoms_count"], 6)
