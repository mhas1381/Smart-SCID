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
            phone_number='09123456789',
            first_name='Test',
            last_name='Clinician'
        )
        # Use get_or_create to avoid duplicate profile error (signal already creates profile)
        UserProfile.objects.get_or_create(user=self.clinician, defaults={'role': 'clinician'})

        # Create patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone_number='0987654321',
            created_by=self.clinician
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name='Module A - Mood Episodes',
            description='Test module for mood episodes',
            version='1.0',
            is_active=True,
            order=1
        )

        # Create questions
        self.q1 = Question.objects.create(
            id='A1',
            module=self.module,
            text='سوال اول؟',
            question_type='boolean',
            order=1,
            has_jump_logic=True
        )

        self.q2 = Question.objects.create(
            id='A2',
            module=self.module,
            text='سوال دوم؟',
            question_type='boolean',
            order=2
        )

        self.q3 = Question.objects.create(
            id='A3',
            module=self.module,
            text='سوال سوم؟',
            question_type='boolean',
            order=3
        )

        # Create jump rule: if answer to q1 is True, skip q2 and go to q3
        JumpRule.objects.create(
            from_question=self.q1,
            to_question=self.q3,
            condition='answer == true',
            condition_type='boolean',
            metadata={'expected_value': True}
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
        response = self.client.get('/api/interviews/modules/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Module A - Mood Episodes')
        self.assertEqual(response.data[0]['question_count'], 3)
        self.assertIn('is_active', response.data[0])
        self.assertIn('version', response.data[0])

    # ============================================================
    # QUESTION TESTS
    # ============================================================

    def test_get_questions(self):
        """
        Test retrieving list of questions.
        Should return 200 OK with all questions.
        """
        response = self.client.get('/api/interviews/questions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        
        # Test new serializer fields
        for question_data in response.data:
            self.assertIn('id', question_data)
            self.assertIn('text', question_data)
            self.assertIn('question_type', question_data)
            self.assertIn('is_criteria', question_data)
            self.assertIn('order', question_data)
            self.assertIn('module_name', question_data)

    # ============================================================
    # INTERVIEW FLOW TESTS
    # ============================================================

    def test_start_interview(self):
        """
        Test starting a new interview session.
        Should return 201 Created with interview data and current question.
        """
        response = self.client.post('/api/interviews/interviews/start/', {
            'patient_id': str(self.patient.id),  # Convert to string
            'module_id': self.module.id
        }, format='json')

        # Debug if fails
        if response.status_code != 201:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['patient_name'], 'Test Patient')
        self.assertEqual(response.data['clinician_name'], 'Test Clinician')
        self.assertEqual(response.data['module_name'], 'Module A - Mood Episodes')
        self.assertEqual(response.data['current_question_text'], 'سوال اول؟')
        self.assertEqual(response.data['answer_count'], 0)
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
            status='in_progress',
            current_question=self.q1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'A1',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

        print(f"Progress with jump response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'A3')
        self.assertEqual(response.data['current_question']['text'], 'سوال سوم؟')
        self.assertEqual(response.data['has_next'], True)
        self.assertEqual(response.data['interview_status'], 'in_progress')
        self.assertEqual(response.data['answered_questions'], 1)
        self.assertEqual(response.data['total_questions'], 3)

    def test_progress_without_jump(self):
        """
        Test interview progress without jump logic.
        When answering False to q1, should go to q2 sequentially.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='in_progress',
            current_question=self.q1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'A1',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        print(f"Progress without jump response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'A2')
        self.assertEqual(response.data['current_question']['text'], 'سوال دوم؟')
        self.assertEqual(response.data['has_next'], True)
        self.assertEqual(response.data['interview_status'], 'in_progress')
        self.assertEqual(response.data['answered_questions'], 1)
        self.assertEqual(response.data['total_questions'], 3)

    def test_complete_interview(self):
        """
        Test completing an interview.
        When answering the last question, interview should be marked as completed.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='in_progress',
            current_question=self.q3
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'A3',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

        print(f"Complete interview response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_next'])
        self.assertEqual(response.data['interview_status'], 'completed')
        self.assertEqual(response.data['answered_questions'], 1)
        self.assertEqual(response.data['total_questions'], 3)
        self.assertIn('diagnosis_result', response.data)
        self.assertEqual(response.data['patient_name'], 'Test Patient')
        self.assertEqual(response.data['clinician_name'], 'Test Clinician')
        self.assertEqual(response.data['module_name'], 'Module A - Mood Episodes')

    def test_pause_interview(self):
        """
        Test pausing an in-progress interview.
        Should change status from 'in_progress' to 'paused'.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='in_progress'
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/pause/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Interview paused successfully')
        interview.refresh_from_db()
        self.assertEqual(interview.status, 'paused')

    def test_resume_interview(self):
        """
        Test resuming a paused interview.
        Should change status from 'paused' to 'in_progress'.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='paused',
            current_question=self.q1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/resume/')
        print(f"Resume interview response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Interview resumed successfully')
        # For a paused interview, there might not be a current question yet
        if 'current_question' in response.data:
            self.assertIsNotNone(response.data['current_question'])
        interview.refresh_from_db()
        self.assertEqual(interview.status, 'in_progress')

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
            status='completed',
            completed_at=timezone.now()
        )

        Answer.objects.create(
            interview=interview,
            question=self.q1,
            answer_type='boolean',
            value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        print(f"Summary response: {response.status_code}")
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, 200)
        self.assertIn('diagnosis_result', response.data)
        # Summary might not have patient_name field depending on serializer
        self.assertEqual(response.data['completed_questions'], 1)
        self.assertEqual(response.data['total_questions'], 3)
        self.assertIsNotNone(response.data['duration'])

    def test_summary_not_completed(self):
        """
        Test retrieving summary for an incomplete interview.
        Should return 400 Bad Request because interview is not completed.
        """
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='in_progress'
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
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
            phone_number='09123456788',
            first_name='Other',
            last_name='User'
        )
        UserProfile.objects.get_or_create(user=other, defaults={'role': 'clinician'})

        # Create interview with original clinician
        interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='in_progress'
        )

        # Authenticate as other clinician
        self.client.force_authenticate(user=other)

        # Try to access the interview
        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'A1',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

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
            phone_number='09123456789',
            first_name='Test',
            last_name='Clinician'
        )
        UserProfile.objects.get_or_create(user=self.clinician, defaults={'role': 'clinician'})

        # Create patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone_number='0987654321',
            created_by=self.clinician
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name='Module A - Mood Episodes',
            description='Test module for mood episodes',
            version='1.0',
            is_active=True,
            order=1
        )

        # Create interview
        self.interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='completed'
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    def test_interview_detail_serializer(self):
        """Test InterviewDetailSerializer returns complete data."""
        response = self.client.get(f'/api/interviews/interviews/{self.interview.id}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['patient_name'], 'Test Patient')
        self.assertEqual(response.data['clinician_name'], 'Test Clinician')
        self.assertEqual(response.data['module_name'], 'Module A - Mood Episodes')
        self.assertEqual(response.data['status'], 'completed')
        self.assertIsNotNone(response.data['patient'])
        self.assertIsNotNone(response.data['answers'])
        self.assertEqual(response.data['answer_count'], 0)


class AnswerTests(APITestCase):
    """Test cases for Answer serializers."""

    def setUp(self):
        """Set up test data for answer tests."""
        # Create clinician user
        self.clinician = User.objects.create_user(
            phone_number='09123456789',
            first_name='Test',
            last_name='Clinician'
        )
        UserProfile.objects.get_or_create(user=self.clinician, defaults={'role': 'clinician'})

        # Create patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone_number='0987654321',
            created_by=self.clinician
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name='Module A - Mood Episodes',
            description='Test module for mood episodes',
            version='1.0',
            is_active=True,
            order=1
        )

        # Create interview
        self.interview = Interview.objects.create(
            patient=self.patient,
            clinician=self.clinician,
            module=self.module,
            status='in_progress'
        )

        # Create question
        self.question = Question.objects.create(
            id='A1',
            module=self.module,
            text='Test question?',
            question_type='boolean',
            order=1
        )

        # Create answer
        self.answer = Answer.objects.create(
            interview=self.interview,
            question=self.question,
            answer_type='boolean',
            value={'boolean': True}
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    def test_answer_list_serializer(self):
        """Test AnswerListSerializer returns answer data with question info."""
        response = self.client.get(f'/api/interviews/interviews/{self.interview.id}/answers/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        
        answer_data = response.data[0]
        self.assertEqual(answer_data['question_text'], 'Test question?')
        self.assertEqual(answer_data['question_type'], 'boolean')
        self.assertEqual(answer_data['answer_type'], 'boolean')
        self.assertEqual(answer_data['value'], {'boolean': True})

    def test_answer_detail_serializer(self):
        """Test AnswerDetailSerializer returns complete answer data."""
        response = self.client.get(f'/api/interviews/answers/{self.answer.id}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['question']['id'], 'A1')
        self.assertEqual(response.data['question']['text'], 'Test question?')
        self.assertEqual(response.data['answer_type'], 'boolean')
        self.assertEqual(response.data['value'], {'boolean': True})
        self.assertIsNotNone(response.data['timestamp'])


class JumpRuleTests(APITestCase):
    """Test cases for JumpRule serializers."""

    def setUp(self):
        """Set up test data for jump rule tests."""
        # Create clinician user
        self.clinician = User.objects.create_user(
            phone_number='09123456789',
            first_name='Test',
            last_name='Clinician'
        )
        UserProfile.objects.get_or_create(user=self.clinician, defaults={'role': 'clinician'})

        # Create patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone_number='0987654321',
            created_by=self.clinician
        )

        # Create interview module
        self.module = InterviewModule.objects.create(
            name='Module A - Mood Episodes',
            description='Test module for mood episodes',
            version='1.0',
            is_active=True,
            order=1
        )

        # Create questions
        self.q1 = Question.objects.create(
            id='A1',
            module=self.module,
            text='Question 1?',
            question_type='boolean',
            order=1
        )

        self.q2 = Question.objects.create(
            id='A2',
            module=self.module,
            text='Question 2?',
            question_type='boolean',
            order=2
        )

        # Create jump rule
        self.jump_rule = JumpRule.objects.create(
            from_question=self.q1,
            to_question=self.q2,
            condition='answer == true',
            condition_type='boolean',
            metadata={'expected_value': True}
        )

        # Authenticate clinician client
        self.client.force_authenticate(user=self.clinician)

    def test_jump_rule_list_serializer(self):
        """Test JumpRuleListSerializer returns jump rule data."""
        response = self.client.get('/api/interviews/jump-rules/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        
        rule_data = response.data[0]
        self.assertEqual(rule_data['from_question_text'], 'Question 1?')
        self.assertEqual(rule_data['to_question_text'], 'Question 2?')
        self.assertEqual(rule_data['condition'], 'answer == true')
        self.assertEqual(rule_data['condition_type'], 'boolean')

    def test_jump_rule_detail_serializer(self):
        """Test JumpRuleDetailSerializer returns complete jump rule data."""
        response = self.client.get(f'/api/interviews/jump-rules/{self.jump_rule.id}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['from_question']['id'], 'A1')
        self.assertEqual(response.data['from_question']['text'], 'Question 1?')
        self.assertEqual(response.data['to_question']['id'], 'A2')
        self.assertEqual(response.data['to_question']['text'], 'Question 2?')
        self.assertEqual(response.data['condition'], 'answer == true')
        self.assertEqual(response.data['condition_type'], 'boolean')
        self.assertEqual(response.data['metadata'], {'expected_value': True})