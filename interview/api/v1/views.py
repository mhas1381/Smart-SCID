from rest_framework import status, generics, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema_view , extend_schema, inline_serializer, OpenApiTypes
import logging

from ...models import Interview, InterviewModule, Question, Answer, JumpRule
from .serializers import (
    InterviewListSerializer,
    InterviewDetailSerializer,
    InterviewModuleListSerializer,
    InterviewModuleDetailSerializer,
    QuestionListSerializer,
    QuestionDetailSerializer,
    InterviewStartSerializer,
    InterviewProgressSerializer,
    InterviewSummarySerializer,
    AnswerListSerializer,
    AnswerDetailSerializer,
)
from .openapi.schema import (
    module_list_schema,
    module_detail_schema,
    question_list_schema,
    question_detail_schema,
    interview_list_schema,
    interview_detail_schema,
    interview_start_schema,
    interview_progress_schema,
    interview_pause_schema,
    interview_resume_schema,
    interview_summary_schema,
)

logger = logging.getLogger('interview')


# ============================================================
# 📋 MODULE VIEWS
# ============================================================

@extend_schema_view(
    get=module_list_schema,
)
class ModuleListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewModuleListSerializer

    def get_queryset(self):
        return InterviewModule.objects.filter(is_active=True)


@extend_schema_view(
    get=module_detail_schema,
)
class ModuleDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewModuleListSerializer
    queryset = InterviewModule.objects.filter(is_active=True)
    lookup_field = 'id'


# ============================================================
# ❓ QUESTION VIEWS
# ============================================================

@extend_schema_view(
    get=question_list_schema,
)
class QuestionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionListSerializer

    def get_queryset(self):
        queryset = Question.objects.all()
        module_id = self.request.query_params.get('module_id')
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        return queryset.order_by('order')


@extend_schema_view(
    get=question_detail_schema,
)
class QuestionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionListSerializer
    queryset = Question.objects.all()
    lookup_field = 'id'


# ============================================================
# 🎬 INTERVIEW VIEWS
# ============================================================

@extend_schema_view(
    get=interview_list_schema,
)
class InterviewListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewListSerializer

    def get_queryset(self):
        user = self.request.user
        return Interview.objects.filter(clinician=user)


@extend_schema_view(
    get=interview_detail_schema,
)
class InterviewDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewListSerializer
    queryset = Interview.objects.all()
    lookup_field = 'id'


class InterviewStartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InterviewStartSerializer,
        responses={201: InterviewListSerializer}
    )
    def post(self, request):
        serializer = InterviewStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get validated data - patient_id is now the actual ID
        patient_id = serializer.validated_data['patient_id']
        module_id = serializer.validated_data['module_id']

        # Create interview
        interview = Interview.objects.create(
            patient_id=patient_id,
            clinician=request.user,
            module_id=module_id,
            status='in_progress'
        )

        first_question = Question.objects.filter(
            module=interview.module
        ).order_by('order').first()

        if not first_question:
            return Response(
                {"error": "No questions found for this module"},
                status=status.HTTP_400_BAD_REQUEST
            )

        interview.current_question = first_question
        interview.save()

        return Response(
            InterviewListSerializer(interview).data,
            status=status.HTTP_201_CREATED
        )


class InterviewProgressView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InterviewProgressSerializer,
        responses={
            200: inline_serializer(
                name="ProgressResponse",
                fields={
                    "current_question": QuestionListSerializer(allow_null=True),
                    "has_next": serializers.BooleanField(),
                    "interview_status": serializers.CharField(),
                    "answered_questions": serializers.IntegerField(),
                    "total_questions": serializers.IntegerField(),
                    "diagnosis_result": serializers.DictField(required=False),
                }
            ),
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"},
                status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != 'in_progress':
            return Response(
                {"error": "Interview is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InterviewProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = get_object_or_404(Question, id=serializer.validated_data['question_id'])

        answer, created = Answer.objects.get_or_create(
            interview=interview,
            question=question,
            defaults={
                'answer_type': serializer.validated_data['answer_type'],
                'value': serializer.validated_data['answer_value'],
                'notes': serializer.validated_data.get('notes', '')
            }
        )

        if not created:
            answer.answer_type = serializer.validated_data['answer_type']
            answer.value = serializer.validated_data['answer_value']
            answer.notes = serializer.validated_data.get('notes', '')
            answer.save()

        next_question = self._get_next_question(interview, question)

        if next_question:
            interview.current_question = next_question
            interview.save()
            return Response({
                'current_question': QuestionListSerializer(next_question).data,
                'has_next': True,
                'interview_status': interview.status,
                'answered_questions': interview.answers.count(),
                'total_questions': interview.module.questions.count()
            })

        interview.status = 'completed'
        interview.current_question = None
        interview.completed_at = timezone.now()
        interview.save()

        return Response({
            'current_question': None,
            'has_next': False,
            'interview_status': 'completed',
            'answered_questions': interview.answers.count(),
            'total_questions': interview.module.questions.count(),
            'diagnosis_result': self._calculate_diagnosis(interview)
        })

    def _get_next_question(self, interview, current_question):
        jump_rules = JumpRule.objects.filter(from_question=current_question)

        for rule in jump_rules:
            if self._evaluate_jump_condition(rule, interview):
                return rule.to_question if rule.to_question else None

        return Question.objects.filter(
            module=interview.module,
            order__gt=current_question.order
        ).order_by('order').first()

    def _evaluate_jump_condition(self, rule, interview):
        try:
            answer = Answer.objects.get(interview=interview, question=rule.from_question)

            if rule.condition_type == 'boolean':
                return answer.boolean_value == rule.metadata.get('expected_value', True)
            elif rule.condition_type == 'multiple_choice':
                return answer.text_value == rule.metadata.get('expected_value', '')
            elif rule.condition_type == 'text':
                pattern = rule.metadata.get('match_pattern', '')
                return pattern.lower() in answer.text_value.lower()
            elif rule.condition_type == 'range':
                min_val = rule.metadata.get('min_value', 0)
                max_val = rule.metadata.get('max_value', float('inf'))
                return min_val <= answer.number_value <= max_val
        except Answer.DoesNotExist:
            return False

        return False

    def _calculate_diagnosis(self, interview):
        result = {'module': interview.module.name}

        if 'Mood Episodes' in interview.module.name:
            answers = {a.question.id: a for a in interview.answers.all()}

            # Depression: A1 + at least 4 of A2-A9
            depression_criteria = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9']
            depression_count = 0
            depression_met = []

            for qid in depression_criteria:
                ans = answers.get(qid)
                if ans and ans.boolean_value:
                    depression_count += 1
                    depression_met.append(qid)

            # Mania: A29 + at least 3 of A30-A38
            mania_criteria = ['A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36', 'A37', 'A38']
            mania_count = 0
            mania_met = []

            for qid in mania_criteria:
                ans = answers.get(qid)
                if ans and ans.boolean_value:
                    mania_count += 1
                    mania_met.append(qid)

            # Hypomania: A41 + at least 3 of A42-A50
            hypomania_criteria = ['A41', 'A42', 'A43', 'A44', 'A45', 'A46', 'A47', 'A48', 'A49', 'A50']
            hypomania_count = 0
            hypomania_met = []

            for qid in hypomania_criteria:
                ans = answers.get(qid)
                if ans and ans.boolean_value:
                    hypomania_count += 1
                    hypomania_met.append(qid)

            result.update({
                'depression': {
                    'diagnosed': depression_count >= 5,
                    'symptoms_counted': depression_count,
                    'required_symptoms_count': 5,
                    'criteria_met': depression_met
                },
                'mania': {
                    'diagnosed': mania_count >= 4,
                    'symptoms_counted': mania_count,
                    'required_symptoms_count': 4,
                    'criteria_met': mania_met
                },
                'hypomania': {
                    'diagnosed': hypomania_count >= 4,
                    'symptoms_counted': hypomania_count,
                    'required_symptoms_count': 4,
                    'criteria_met': hypomania_met
                }
            })

        return result


class InterviewPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return None

    @extend_schema(
        responses={200: inline_serializer(name="PauseResponse", fields={"message": serializers.CharField()})}
    )
    def post(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"},
                status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != 'in_progress':
            return Response(
                {"error": "Interview is not in progress"},
                status=status.HTTP_400_BAD_REQUEST
            )

        interview.status = 'paused'
        interview.save()

        return Response({"message": "Interview paused successfully"})


class InterviewResumeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="ResumeResponse",
                fields={
                    "message": serializers.CharField(),
                    "current_question": QuestionListSerializer(allow_null=True),
                }
            )
        }
    )
    def post(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"},
                status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != 'paused':
            return Response(
                {"error": "Interview is not paused"},
                status=status.HTTP_400_BAD_REQUEST
            )

        interview.status = 'in_progress'
        interview.save()

        return Response({
            "message": "Interview resumed successfully",
            "current_question": QuestionListSerializer(interview.current_question).data if interview.current_question else None
        })


class InterviewSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="SummaryResponse",
                fields={
                    "interview_id": serializers.CharField(),
                    "diagnosis_result": serializers.DictField(),
                    "completed_questions": serializers.IntegerField(),
                    "total_questions": serializers.IntegerField(),
                    "completion_percentage": serializers.FloatField(),
                }
            )
        }
    )
    def get(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"},
                status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != 'completed':
            return Response(
                {"error": "Interview is not completed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        progress_view = InterviewProgressView()
        diagnosis = progress_view._calculate_diagnosis(interview)

        return Response({
            'interview_id': str(interview.id),
            'diagnosis_result': diagnosis,
            'completed_questions': interview.answers.count(),
            'total_questions': interview.module.questions.count(),
            'completion_percentage': (
                (interview.answers.count() / interview.module.questions.count()) * 100
                if interview.module.questions.count() > 0 else 0
            )
        })