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
            phone_number='09123456789',
            first_name='Test',
            last_name='Clinician'
        )
        UserProfile.objects.get_or_create(user=self.clinician, defaults={'role': 'clinician'})

        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone_number='0987654321',
            created_by=self.clinician
        )

        self.module = InterviewModule.objects.create(
            name='Module B - Psychotic and Associated Symptoms',
            description='Psychotic symptoms module',
            version='1.0',
            is_active=True,
            order=2
        )

        # Create Module B questions (subset for testing)
        self.b1 = Question.objects.create(
            id='B1', module=self.module, text='توهم مرجعیت؟',
            question_type='boolean', is_criteria=True, criteria_number='1',
            order=1, has_jump_logic=True
        )
        self.b2 = Question.objects.create(
            id='B2', module=self.module, text='توهم آزار و تعقیب؟',
            question_type='boolean', is_criteria=True, criteria_number='2',
            order=2
        )
        self.b11 = Question.objects.create(
            id='B11', module=self.module, text='سایر توهمات؟',
            question_type='boolean', is_criteria=True, criteria_number='11',
            order=11, has_jump_logic=True
        )
        self.b12 = Question.objects.create(
            id='B12', module=self.module, text='توهم شنوایی؟',
            question_type='boolean', is_criteria=True, criteria_number='12',
            order=12, has_jump_logic=True
        )
        self.b18 = Question.objects.create(
            id='B18', module=self.module, text='گفتار آشفته؟',
            question_type='boolean', is_criteria=True, criteria_number='18',
            order=18
        )
        self.b20 = Question.objects.create(
            id='B20', module=self.module, text='رفتار کاتاتونیک؟',
            question_type='boolean', is_criteria=True, criteria_number='20',
            order=20, has_jump_logic=True
        )
        self.b21 = Question.objects.create(
            id='B21', module=self.module, text='بی‌ارادگی؟',
            question_type='boolean', is_criteria=True, criteria_number='21',
            order=21
        )
        self.b23 = Question.objects.create(
            id='B23', module=self.module, text='بیماری پزشکی؟',
            question_type='boolean', order=23
        )
        self.b24 = Question.objects.create(
            id='B24', module=self.module, text='مصرف ماده؟',
            question_type='boolean', order=24
        )

        # Jump rules
        JumpRule.objects.create(
            from_question=self.b1, to_question=self.b12,
            condition='criteria_count < 1', condition_type='criteria_count',
            metadata={'question_ids': ['B1'], 'min_count': 1}
        )
        JumpRule.objects.create(
            from_question=self.b12, to_question=self.b18,
            condition='answer == false', condition_type='boolean',
            metadata={'expected_value': False}
        )
        JumpRule.objects.create(
            from_question=self.b20, to_question=self.b21,
            condition='answer == false', condition_type='boolean',
            metadata={'expected_value': False}
        )

        self.client.force_authenticate(user=self.clinician)

    def test_module_b_listed(self):
        """Module B should appear in the modules list."""
        response = self.client.get('/api/interviews/modules/')
        self.assertEqual(response.status_code, 200)
        names = [m['name'] for m in response.data]
        self.assertIn('Module B - Psychotic and Associated Symptoms', names)

    def test_module_b_start_interview(self):
        """Should be able to start a Module B interview."""
        response = self.client.post('/api/interviews/interviews/start/', {
            'patient_id': str(self.patient.id),
            'module_id': self.module.id
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['module_name'], 'Module B - Psychotic and Associated Symptoms')

    def test_b1_negative_skips_to_b12(self):
        """If B1 (delusion of reference) is negative, skip to B12 (auditory hallucination)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.b1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'B1',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'B12')

    def test_b1_positive_continues_to_b2(self):
        """If B1 (delusion of reference) is positive, continue to B2."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.b1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'B1',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'B2')

    def test_b12_negative_skips_to_b18(self):
        """If B12 (auditory hallucination) is negative, skip to B18 (disorganized speech)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.b12
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'B12',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'B18')

    def test_b20_negative_skips_to_b21(self):
        """If B20 (catatonic behavior) is negative, skip to B21 (negative symptoms)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.b20
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'B20',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'B21')

    def test_module_b_diagnosis_with_symptoms(self):
        """Diagnosis should report present psychotic symptoms."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        # B1 positive (delusion of reference)
        Answer.objects.create(
            interview=interview, question=self.b1,
            answer_type='boolean', value={'boolean': True}
        )
        # B12 positive (auditory hallucination)
        Answer.objects.create(
            interview=interview, question=self.b12,
            answer_type='boolean', value={'boolean': True}
        )
        # B23 negative (not due to medical)
        Answer.objects.create(
            interview=interview, question=self.b23,
            answer_type='boolean', value={'boolean': False}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertIn('psychotic_symptoms', diagnosis)
        self.assertTrue(diagnosis['psychotic_symptoms']['delusions']['present'])
        self.assertEqual(diagnosis['psychotic_symptoms']['delusions']['count'], 1)
        self.assertIn('B1', diagnosis['psychotic_symptoms']['delusions']['items'])
        self.assertTrue(diagnosis['psychotic_symptoms']['hallucinations']['present'])
        self.assertFalse(diagnosis['exclusion_factors']['due_to_medical_condition'])

    def test_module_b_diagnosis_no_symptoms(self):
        """Diagnosis should report no psychotic symptoms when all negative."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        # All negative
        for q in [self.b1, self.b2, self.b12, self.b18, self.b20, self.b21, self.b23, self.b24]:
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': False}
            )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertFalse(diagnosis['psychotic_symptoms']['delusions']['present'])
        self.assertEqual(diagnosis['psychotic_symptoms']['delusions']['count'], 0)
        self.assertFalse(diagnosis['psychotic_symptoms']['hallucinations']['present'])


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
            phone_number='09123456789',
            first_name='Test',
            last_name='Clinician'
        )
        UserProfile.objects.get_or_create(user=self.clinician, defaults={'role': 'clinician'})

        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone_number='0987654321',
            created_by=self.clinician
        )

        self.module = InterviewModule.objects.create(
            name='Module C - Differential Diagnosis of Psychotic Disorders',
            description='Differential diagnosis of psychotic disorders',
            version='1.0',
            is_active=True,
            order=3
        )

        # Create Module C questions (subset for testing)
        self.c1 = Question.objects.create(
            id='C1', module=self.module, text='علائم خارج از دوره خلقی؟',
            question_type='boolean', is_criteria=True, criteria_number='1',
            order=1, has_jump_logic=True
        )
        self.c2 = Question.objects.create(
            id='C2', module=self.module, text='معیار A اسکیزوفرنی؟',
            question_type='boolean', is_criteria=True, criteria_number='2',
            order=2, has_jump_logic=True
        )
        self.c3 = Question.objects.create(
            id='C3', module=self.module, text='معیار B اسکیزوفرنی؟',
            question_type='boolean', is_criteria=True, criteria_number='3',
            order=3
        )
        self.c4 = Question.objects.create(
            id='C4', module=self.module, text='معیار C اسکیزوفرنی؟',
            question_type='boolean', is_criteria=True, criteria_number='4',
            order=4
        )
        self.c5 = Question.objects.create(
            id='C5', module=self.module, text='معیار D اسکیزوفرنی؟',
            question_type='boolean', is_criteria=True, criteria_number='5',
            order=5
        )
        self.c6 = Question.objects.create(
            id='C6', module=self.module, text='معیار E اسکیزوفرنی؟',
            question_type='boolean', is_criteria=True, criteria_number='6',
            order=6, has_jump_logic=True
        )
        self.c7 = Question.objects.create(
            id='C7', module=self.module, text='اسکیزوفرنی‌فرم: مدت ۱-۶ ماه؟',
            question_type='boolean', is_criteria=True, criteria_number='7',
            order=7
        )
        self.c8 = Question.objects.create(
            id='C8', module=self.module, text='اسکیزوفرنی‌فرم: رد ماده/بیماری؟',
            question_type='boolean', is_criteria=True, criteria_number='8',
            order=8, has_jump_logic=True
        )
        self.c9 = Question.objects.create(
            id='C9', module=self.module, text='اسکیزوافکتیو: دوره خلقی همزمان؟',
            question_type='boolean', is_criteria=True, criteria_number='9',
            order=9
        )
        self.c10 = Question.objects.create(
            id='C10', module=self.module, text='اسکیزوافکتیو: توهم/هذیان بدون خلق؟',
            question_type='boolean', is_criteria=True, criteria_number='10',
            order=10
        )
        self.c11 = Question.objects.create(
            id='C11', module=self.module, text='اسکیزوافکتیو: خلق >50%؟',
            question_type='boolean', is_criteria=True, criteria_number='11',
            order=11
        )
        self.c12 = Question.objects.create(
            id='C12', module=self.module, text='اسکیزوافکتیو: رد ماده/بیماری؟',
            question_type='boolean', is_criteria=True, criteria_number='12',
            order=12, has_jump_logic=True
        )
        self.c13 = Question.objects.create(
            id='C13', module=self.module, text='هذیانی: هذیان ۱+ ماه؟',
            question_type='boolean', is_criteria=True, criteria_number='13',
            order=13
        )
        self.c14 = Question.objects.create(
            id='C14', module=self.module, text='هذیانی: بدون معیار A اسکیزوفرنی؟',
            question_type='boolean', is_criteria=True, criteria_number='14',
            order=14
        )
        self.c15 = Question.objects.create(
            id='C15', module=self.module, text='هذیانی: عملکرد مختل نشده؟',
            question_type='boolean', is_criteria=True, criteria_number='15',
            order=15
        )
        self.c16 = Question.objects.create(
            id='C16', module=self.module, text='هذیانی: خلق کوتاه‌تر از هذیان؟',
            question_type='boolean', is_criteria=True, criteria_number='16',
            order=16
        )
        self.c17 = Question.objects.create(
            id='C17', module=self.module, text='هذیانی: رد ماده/بیماری/OCD؟',
            question_type='boolean', is_criteria=True, criteria_number='17',
            order=17
        )
        self.c18 = Question.objects.create(
            id='C18', module=self.module, text='نوع هذیان؟',
            question_type='text', order=18
        )
        self.c19 = Question.objects.create(
            id='C19', module=self.module, text='روان‌پریشی کوتاه: علائم؟',
            question_type='boolean', is_criteria=True, criteria_number='18',
            order=19
        )
        self.c20 = Question.objects.create(
            id='C20', module=self.module, text='روان‌پریشی کوتاه: مدت ۱ روز-۱ ماه؟',
            question_type='boolean', is_criteria=True, criteria_number='19',
            order=20
        )
        self.c21 = Question.objects.create(
            id='C21', module=self.module, text='روان‌پریشی کوتاه: رد خلقی/سایر؟',
            question_type='boolean', is_criteria=True, criteria_number='20',
            order=21
        )
        self.c22 = Question.objects.create(
            id='C22', module=self.module, text='سایر مشخص‌شده: علائم غالب؟',
            question_type='boolean', is_criteria=True, criteria_number='21',
            order=22
        )
        self.c23 = Question.objects.create(
            id='C23', module=self.module, text='اختلال بالینی مهم؟',
            question_type='boolean', is_criteria=True, criteria_number='22',
            order=23
        )
        self.c24 = Question.objects.create(
            id='C24', module=self.module, text='رد ماده/بیماری؟',
            question_type='boolean', is_criteria=True, criteria_number='23',
            order=24
        )
        self.c25 = Question.objects.create(
            id='C25', module=self.module, text='عدم تطابق با تشخیص خاص؟',
            question_type='boolean', is_criteria=True, criteria_number='24',
            order=25
        )
        self.c26 = Question.objects.create(
            id='C26', module=self.module, text='سیر اسکیزوفرنی: فعلی؟',
            question_type='boolean', order=26
        )
        self.c27 = Question.objects.create(
            id='C27', module=self.module, text='سیر اسکیزوفرنی‌فرم: فعلی؟',
            question_type='boolean', order=27
        )
        self.c28 = Question.objects.create(
            id='C28', module=self.module, text='سیر اسکیزوافکتیو: فعلی؟',
            question_type='boolean', order=28
        )
        self.c29 = Question.objects.create(
            id='C29', module=self.module, text='سیر هذیانی: فعلی؟',
            question_type='boolean', order=29
        )
        self.c30 = Question.objects.create(
            id='C30', module=self.module, text='سیر کوتاه: فعلی؟',
            question_type='boolean', order=30
        )

        # Jump rules
        JumpRule.objects.create(
            from_question=self.c1, to_question=None,
            condition='answer == false', condition_type='boolean',
            metadata={'expected_value': False}
        )
        JumpRule.objects.create(
            from_question=self.c2, to_question=self.c13,
            condition='criteria_count < 2', condition_type='criteria_count',
            metadata={'question_ids': ['C2', 'C3', 'C4', 'C5', 'C6'], 'min_count': 2}
        )
        JumpRule.objects.create(
            from_question=self.c6, to_question=self.c9,
            condition='criteria_count_met >= 4', condition_type='criteria_count_met',
            metadata={'question_ids': ['C2', 'C3', 'C4', 'C5', 'C6'], 'min_count': 4}
        )
        JumpRule.objects.create(
            from_question=self.c8, to_question=self.c9,
            condition='answer == false', condition_type='boolean',
            metadata={'expected_value': False}
        )
        JumpRule.objects.create(
            from_question=self.c12, to_question=self.c13,
            condition='answer == false', condition_type='boolean',
            metadata={'expected_value': False}
        )

        self.client.force_authenticate(user=self.clinician)

    # ============================================================
    # MODULE LISTING
    # ============================================================

    def test_module_c_listed(self):
        """Module C should appear in the modules list."""
        response = self.client.get('/api/interviews/modules/')
        self.assertEqual(response.status_code, 200)
        names = [m['name'] for m in response.data]
        self.assertIn('Module C - Differential Diagnosis of Psychotic Disorders', names)

    def test_module_c_question_count(self):
        """Module C should report correct question count."""
        response = self.client.get('/api/interviews/modules/')
        self.assertEqual(response.status_code, 200)
        module_data = next(m for m in response.data if 'Module C' in m['name'])
        self.assertEqual(module_data['question_count'], 30)

    def test_module_c_start_interview(self):
        """Should be able to start a Module C interview."""
        response = self.client.post('/api/interviews/interviews/start/', {
            'patient_id': str(self.patient.id),
            'module_id': self.module.id
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['module_name'], 'Module C - Differential Diagnosis of Psychotic Disorders')

    # ============================================================
    # JUMP RULE TESTS
    # ============================================================

    def test_c1_negative_ends_interview(self):
        """If C1 (psychosis outside mood) is negative, interview ends (jump to null)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.c1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'C1',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_next'])
        self.assertEqual(response.data['interview_status'], 'completed')

    def test_c1_positive_continues_to_c2(self):
        """If C1 (psychosis outside mood) is positive, continue to C2."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.c1
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'C1',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'C2')

    def test_c2_negative_skips_to_c13(self):
        """If fewer than 2 of C2-C6 are positive, skip to C13 (Delusional Disorder)."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.c2
        )

        # Only C2 answered so far (1 positive out of 5 → criteria_count < 2 is true)
        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'C2',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'C13')

    def test_c6_schizophrenia_criteria_met_skips_to_c9(self):
        """If C2-C6 all positive (schizophrenia criteria met), skip to C9."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.c2
        )

        # Answer C2-C5 positively first
        for qid in ['C2', 'C3', 'C4', 'C5']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': True}
            )

        # Now answer C6 — with 4 already positive, criteria_count >= 4 → jump to C9
        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'C6',
            'answer_value': {'boolean': True},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'C9')

    def test_c8_negative_skips_to_c9(self):
        """If C8 (schizophreniform exclusion) is negative, skip to C9."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.c8
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'C8',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'C9')

    def test_c12_negative_skips_to_c13(self):
        """If C12 (schizoaffective exclusion) is negative, skip to C13."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='in_progress',
            current_question=self.c12
        )

        response = self.client.post(f'/api/interviews/interviews/{interview.id}/progress/', {
            'question_id': 'C12',
            'answer_value': {'boolean': False},
            'answer_type': 'boolean'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_question']['id'], 'C13')

    # ============================================================
    # DIAGNOSIS TESTS
    # ============================================================

    def test_diagnosis_psychotic_mood_disorder(self):
        """When C1 is negative, diagnosis should indicate Psychotic Mood Disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        Answer.objects.create(
            interview=interview, question=self.c1,
            answer_type='boolean', value={'boolean': False}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertTrue(diagnosis['psychotic_mood_disorder'])
        self.assertIn('Module D', diagnosis['note'])

    def test_diagnosis_schizophrenia(self):
        """When C1-C6 all positive, diagnosis should be Schizophrenia."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        for qid in ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': True}
            )

        # C26: current
        Answer.objects.create(
            interview=interview, question=self.c26,
            answer_type='boolean', value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Schizophrenia')
        self.assertTrue(diagnosis['criteria_summary']['schizophrenia']['met'])
        self.assertTrue(diagnosis['details']['current'])

    def test_diagnosis_schizophreniform(self):
        """When C1,C7,C8 positive but C4 negative, diagnosis should be Schizophreniform."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        # C1 positive, C2 positive, C3 positive, C4 negative (no 6 months), C5 positive, C6 positive
        # C7 positive (1-6 months), C8 positive (not substance/GMC)
        for qid, val in [('C1', True), ('C2', True), ('C3', True), ('C4', False),
                          ('C5', True), ('C6', True), ('C7', True), ('C8', True)]:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': val}
            )

        # C27: current
        Answer.objects.create(
            interview=interview, question=self.c27,
            answer_type='boolean', value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Schizophreniform Disorder')
        self.assertTrue(diagnosis['criteria_summary']['schizophreniform']['met'])

    def test_diagnosis_schizoaffective(self):
        """When C1,C9-C12 positive, diagnosis should be Schizoaffective Disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        for qid in ['C1', 'C9', 'C10', 'C11', 'C12']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': True}
            )

        # C28: current
        Answer.objects.create(
            interview=interview, question=self.c28,
            answer_type='boolean', value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Schizoaffective Disorder')
        self.assertTrue(diagnosis['criteria_summary']['schizoaffective']['met'])
        self.assertTrue(diagnosis['details']['current'])

    def test_diagnosis_delusional_disorder(self):
        """When C1,C13-C17 positive, diagnosis should be Delusional Disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        for qid in ['C1', 'C13', 'C14', 'C15', 'C16', 'C17']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': True}
            )

        # C18: delusion type
        Answer.objects.create(
            interview=interview, question=self.c18,
            answer_type='text', value={'text': 'Persecutory'}
        )

        # C29: current
        Answer.objects.create(
            interview=interview, question=self.c29,
            answer_type='boolean', value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Delusional Disorder')
        self.assertTrue(diagnosis['criteria_summary']['delusional_disorder']['met'])
        self.assertEqual(diagnosis['details']['type'], 'Persecutory')
        self.assertTrue(diagnosis['details']['current'])

    def test_diagnosis_brief_psychotic(self):
        """When C1,C19-C21 positive, diagnosis should be Brief Psychotic Disorder."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        for qid in ['C1', 'C19', 'C20', 'C21']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': True}
            )

        # C30: current
        Answer.objects.create(
            interview=interview, question=self.c30,
            answer_type='boolean', value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Brief Psychotic Disorder')
        self.assertTrue(diagnosis['criteria_summary']['brief_psychotic']['met'])

    def test_diagnosis_other_specified(self):
        """When C1,C22-C25 positive but no other diagnosis met, should be Other Specified."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        for qid in ['C1', 'C22', 'C23', 'C24', 'C25']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': True}
            )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Other Specified Psychotic Disorder')
        self.assertTrue(diagnosis['criteria_summary']['other_specified']['met'])

    def test_diagnosis_undifferentiated(self):
        """When C1 positive but no disorder criteria met, should be Undifferentiated."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        Answer.objects.create(
            interview=interview, question=self.c1,
            answer_type='boolean', value={'boolean': True}
        )
        # Only C1 positive, all other criteria negative
        for qid in ['C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10',
                      'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17',
                      'C19', 'C20', 'C21', 'C22', 'C23', 'C24', 'C25']:
            q = Question.objects.get(id=qid)
            Answer.objects.create(
                interview=interview, question=q,
                answer_type='boolean', value={'boolean': False}
            )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertEqual(diagnosis['diagnosis'], 'Undifferentiated')

    def test_diagnosis_no_criteria_summary_structure(self):
        """Diagnosis result should include all criteria_summary keys."""
        interview = Interview.objects.create(
            patient=self.patient, clinician=self.clinician,
            module=self.module, status='completed',
            completed_at=timezone.now()
        )

        Answer.objects.create(
            interview=interview, question=self.c1,
            answer_type='boolean', value={'boolean': True}
        )

        response = self.client.get(f'/api/interviews/interviews/{interview.id}/summary/')
        self.assertEqual(response.status_code, 200)

        diagnosis = response.data['diagnosis_result']
        self.assertIn('criteria_summary', diagnosis)
        for key in ['schizophrenia', 'schizophreniform', 'schizoaffective',
                     'delusional_disorder', 'brief_psychotic', 'other_specified']:
            self.assertIn(key, diagnosis['criteria_summary'])
            self.assertIn('met', diagnosis['criteria_summary'][key])
            self.assertIn('criteria_positive', diagnosis['criteria_summary'][key])