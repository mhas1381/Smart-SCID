from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema_view,
)
import logging

from ...models import Interview, InterviewModule, Question, Answer, JumpRule
from .serializers import (
    InterviewListSerializer,
    InterviewDetailSerializer,
    InterviewModuleListSerializer,
    QuestionListSerializer,
    QuestionDetailSerializer,
    InterviewStartSerializer,
    InterviewProgressSerializer,
    AnswerListSerializer,
    AnswerDetailSerializer,
    JumpRuleListSerializer,
    JumpRuleDetailSerializer,
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

logger = logging.getLogger("interview")


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
    lookup_field = "id"


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
        module_id = self.request.query_params.get("module_id")
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        return queryset.order_by("order")


@extend_schema_view(
    get=question_detail_schema,
)
class QuestionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionListSerializer
    queryset = Question.objects.all()
    lookup_field = "id"


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
    serializer_class = InterviewDetailSerializer

    def get_queryset(self):
        return Interview.objects.all()

    lookup_field = "id"


@extend_schema_view(
    post=interview_start_schema,
)
class InterviewStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InterviewStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get validated data - patient_id is now the actual ID
        patient_id = serializer.validated_data["patient_id"]
        module_id = serializer.validated_data["module_id"]

        # Create interview
        interview = Interview.objects.create(
            patient_id=patient_id,
            clinician=request.user,
            module_id=module_id,
            status="in_progress",
        )

        first_question = (
            Question.objects.filter(module=interview.module).order_by("order").first()
        )

        if not first_question:
            return Response(
                {"error": "No questions found for this module"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interview.current_question = first_question
        interview.save()

        return Response(
            InterviewListSerializer(interview).data, status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    post=interview_progress_schema,
)
class InterviewProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"}, status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != "in_progress":
            return Response(
                {"error": "Interview is not in progress"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InterviewProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = get_object_or_404(
            Question, id=serializer.validated_data["question_id"]
        )

        answer, created = Answer.objects.get_or_create(
            interview=interview,
            question=question,
            defaults={
                "answer_type": serializer.validated_data["answer_type"],
                "value": self._extract_answer_value(serializer),
                "notes": serializer.validated_data.get("notes", ""),
            },
        )

        if not created:
            answer.answer_type = serializer.validated_data["answer_type"]
            answer.value = self._extract_answer_value(serializer)
            answer.notes = serializer.validated_data.get("notes", "")
            answer.save()

        next_question = self._get_next_question(interview, question)

        if next_question:
            interview.current_question = next_question
            interview.save()
            return Response(
                {
                    "current_question": QuestionListSerializer(next_question).data,
                    "has_next": True,
                    "interview_status": interview.status,
                    "answered_questions": interview.answers.count(),
                    "total_questions": interview.module.questions.count(),
                }
            )

        interview.status = "completed"
        interview.current_question = None
        interview.completed_at = timezone.now()
        interview.save()

        return Response(
            {
                "current_question": None,
                "has_next": False,
                "interview_status": "completed",
                "answered_questions": interview.answers.count(),
                "total_questions": interview.module.questions.count(),
                "diagnosis_result": self._calculate_diagnosis(interview),
                "patient_name": interview.patient.get_full_name(),
                "clinician_name": interview.clinician.get_full_name(),
                "module_name": interview.module.name,
            }
        )

    def _extract_answer_value(self, serializer):
        """Extract the actual answer value, unwrapping nested dicts like {'boolean': True}"""
        value = serializer.validated_data["answer_value"]
        answer_type = serializer.validated_data["answer_type"]
        if isinstance(value, dict) and answer_type in value:
            return value[answer_type]
        return value

    def _get_next_question(self, interview, current_question):
        jump_rules = JumpRule.objects.filter(from_question=current_question)

        for rule in jump_rules:
            if self._evaluate_jump_condition(rule, interview):
                return rule.to_question if rule.to_question else None

        return (
            Question.objects.filter(
                module=interview.module, order__gt=current_question.order
            )
            .order_by("order")
            .first()
        )

    def _evaluate_jump_condition(self, rule, interview):
        try:
            answer = Answer.objects.get(
                interview=interview, question=rule.from_question
            )

            if rule.condition_type == "boolean":
                return answer.boolean_value == rule.metadata.get("expected_value", True)
            elif rule.condition_type == "multiple_choice":
                return answer.text_value == rule.metadata.get("expected_value", "")
            elif rule.condition_type == "text":
                pattern = rule.metadata.get("match_pattern", "")
                return pattern.lower() in answer.text_value.lower()
            elif rule.condition_type == "range":
                min_val = rule.metadata.get("min_value", 0)
                max_val = rule.metadata.get("max_value", float("inf"))
                return min_val <= answer.number_value <= max_val
            elif rule.condition_type == "criteria_count":
                question_ids = rule.metadata.get("question_ids", [])
                min_count = rule.metadata.get("min_count", 1)
                positive_count = Answer.objects.filter(
                    interview=interview, question_id__in=question_ids
                )
                count = sum(1 for a in positive_count if a.boolean_value)
                return count < min_count
            elif rule.condition_type == "criteria_count_met":
                question_ids = rule.metadata.get("question_ids", [])
                min_count = rule.metadata.get("min_count", 1)
                positive_count = Answer.objects.filter(
                    interview=interview, question_id__in=question_ids
                )
                count = sum(1 for a in positive_count if a.boolean_value)
                return count >= min_count
        except Answer.DoesNotExist:
            return False

        return False

    def _calculate_diagnosis(self, interview):
        result = {"module": interview.module.name}

        if "Mood Episodes" in interview.module.name:
            answers = {a.question.id: a for a in interview.answers.all()}

            # Depression: A1 + at least 4 of A2-A9
            depression_criteria = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]
            depression_count = 0
            depression_met = []

            for qid in depression_criteria:
                ans = answers.get(qid)
                if ans and ans.boolean_value:
                    depression_count += 1
                    depression_met.append(qid)

            # Mania: A29 + at least 3 of A30-A38
            mania_criteria = [
                "A29",
                "A30",
                "A31",
                "A32",
                "A33",
                "A34",
                "A35",
                "A36",
                "A37",
                "A38",
            ]
            mania_count = 0
            mania_met = []

            for qid in mania_criteria:
                ans = answers.get(qid)
                if ans and ans.boolean_value:
                    mania_count += 1
                    mania_met.append(qid)

            # Hypomania: A41 + at least 3 of A42-A50
            hypomania_criteria = [
                "A41",
                "A42",
                "A43",
                "A44",
                "A45",
                "A46",
                "A47",
                "A48",
                "A49",
                "A50",
            ]
            hypomania_count = 0
            hypomania_met = []

            for qid in hypomania_criteria:
                ans = answers.get(qid)
                if ans and ans.boolean_value:
                    hypomania_count += 1
                    hypomania_met.append(qid)

            result.update(
                {
                    "depression": {
                        "diagnosed": depression_count >= 5,
                        "symptoms_counted": depression_count,
                        "required_symptoms_count": 5,
                        "criteria_met": depression_met,
                    },
                    "mania": {
                        "diagnosed": mania_count >= 4,
                        "symptoms_counted": mania_count,
                        "required_symptoms_count": 4,
                        "criteria_met": mania_met,
                    },
                    "hypomania": {
                        "diagnosed": hypomania_count >= 4,
                        "symptoms_counted": hypomania_count,
                        "required_symptoms_count": 4,
                        "criteria_met": hypomania_met,
                    },
                }
            )

        elif "Differential Diagnosis of Psychotic" in interview.module.name:
            answers = {a.question.id: a for a in interview.answers.all()}

            # C1: Psychotic symptoms outside mood episodes?
            c1_positive = answers.get("C1") and answers["C1"].boolean_value

            if not c1_positive:
                result["psychotic_mood_disorder"] = True
                result["note"] = (
                    "Psychotic symptoms occur only during mood episodes. "
                    "This is a Psychotic Mood Disorder. Proceed to Module D for mood diagnosis."
                )
            else:
                # Evaluate schizophrenia criteria (C2-C6)
                schizo_criteria = ["C2", "C3", "C4", "C5", "C6"]
                schizo_met = [
                    qid
                    for qid in schizo_criteria
                    if answers.get(qid) and answers[qid].boolean_value
                ]
                schizophrenia = len(schizo_met) == 5

                # Schizophreniform: C7 + C8 (same as schizophrenia but 1-6 months)
                schizoform_met = [
                    qid
                    for qid in ["C7", "C8"]
                    if answers.get(qid) and answers[qid].boolean_value
                ]
                schizophreniform = len(schizoform_met) == 2

                # Schizoaffective: C9-C12
                schizoaffective_criteria = ["C9", "C10", "C11", "C12"]
                schizoaffective_met = [
                    qid
                    for qid in schizoaffective_criteria
                    if answers.get(qid) and answers[qid].boolean_value
                ]
                schizoaffective = len(schizoaffective_met) == 4

                # Delusional disorder: C13-C17
                delusional_criteria = ["C13", "C14", "C15", "C16", "C17"]
                delusional_met = [
                    qid
                    for qid in delusional_criteria
                    if answers.get(qid) and answers[qid].boolean_value
                ]
                delusional = len(delusional_met) == 5

                # Brief psychotic: C19-C21
                brief_criteria = ["C19", "C20", "C21"]
                brief_met = [
                    qid
                    for qid in brief_criteria
                    if answers.get(qid) and answers[qid].boolean_value
                ]
                brief_psychotic = len(brief_met) == 3

                # Other specified: C22-C25
                other_criteria = ["C22", "C23", "C24", "C25"]
                other_met = [
                    qid
                    for qid in other_criteria
                    if answers.get(qid) and answers[qid].boolean_value
                ]
                other_specified = len(other_met) == 4

                # Determine primary diagnosis
                diagnosis = "Undifferentiated"
                diagnosis_details = {}

                if schizophrenia:
                    diagnosis = "Schizophrenia"
                    diagnosis_details["criteria_met"] = schizo_met
                    if answers.get("C26"):
                        diagnosis_details["current"] = answers["C26"].boolean_value
                elif schizophreniform:
                    diagnosis = "Schizophreniform Disorder"
                    diagnosis_details["criteria_met"] = schizoform_met
                    if answers.get("C27"):
                        diagnosis_details["current"] = answers["C27"].boolean_value
                elif schizoaffective:
                    diagnosis = "Schizoaffective Disorder"
                    diagnosis_details["criteria_met"] = schizoaffective_met
                    if answers.get("C28"):
                        diagnosis_details["current"] = answers["C28"].boolean_value
                elif delusional:
                    diagnosis = "Delusional Disorder"
                    diagnosis_details["criteria_met"] = delusional_met
                    delusion_type = answers.get("C18")
                    if delusion_type:
                        diagnosis_details["type"] = delusion_type.text_value
                    if answers.get("C29"):
                        diagnosis_details["current"] = answers["C29"].boolean_value
                elif brief_psychotic:
                    diagnosis = "Brief Psychotic Disorder"
                    diagnosis_details["criteria_met"] = brief_met
                    if answers.get("C30"):
                        diagnosis_details["current"] = answers["C30"].boolean_value
                elif other_specified:
                    diagnosis = "Other Specified Psychotic Disorder"
                    diagnosis_details["criteria_met"] = other_met

                # Module B symptom summary (referenced by Module C)
                module_b_answers = {}
                try:
                    module_b = InterviewModule.objects.get(
                        name__icontains="Psychotic and Associated"
                    )
                    b_answers = Answer.objects.filter(
                        interview__patient=interview.patient,
                        interview__module=module_b,
                        interview__status="completed",
                    ).order_by("-interview__completed_at")

                    if b_answers.exists():
                        latest_b = {}
                        for a in b_answers:
                            if a.question_id not in latest_b:
                                latest_b[a.question_id] = a

                        delusion_ids = [
                            "B1",
                            "B2",
                            "B3",
                            "B4",
                            "B5",
                            "B6",
                            "B7",
                            "B8",
                            "B9",
                            "B10",
                            "B11",
                        ]
                        hallucination_ids = ["B12", "B13", "B14", "B15", "B16", "B17"]

                        module_b_answers = {
                            "delusions_present": [
                                qid
                                for qid in delusion_ids
                                if latest_b.get(qid) and latest_b[qid].boolean_value
                            ],
                            "hallucinations_present": [
                                qid
                                for qid in hallucination_ids
                                if latest_b.get(qid) and latest_b[qid].boolean_value
                            ],
                        }
                except InterviewModule.DoesNotExist:
                    pass

                result.update(
                    {
                        "diagnosis": diagnosis,
                        "details": diagnosis_details,
                        "criteria_summary": {
                            "schizophrenia": {
                                "met": schizophrenia,
                                "criteria_positive": schizo_met,
                            },
                            "schizophreniform": {
                                "met": schizophreniform,
                                "criteria_positive": schizoform_met,
                            },
                            "schizoaffective": {
                                "met": schizoaffective,
                                "criteria_positive": schizoaffective_met,
                            },
                            "delusional_disorder": {
                                "met": delusional,
                                "criteria_positive": delusional_met,
                            },
                            "brief_psychotic": {
                                "met": brief_psychotic,
                                "criteria_positive": brief_met,
                            },
                            "other_specified": {
                                "met": other_specified,
                                "criteria_positive": other_met,
                            },
                        },
                        "module_b_symptoms": module_b_answers,
                    }
                )

        elif "Mood Disorders" in interview.module.name:
            # Module D: Differential Diagnosis of Mood Disorders
            answers = {a.question.id: a for a in interview.answers.all()}

            # D1 gate: clinically significant mood symptoms?
            d1_positive = answers.get("D1") and answers["D1"].boolean_value
            if not d1_positive:
                result["no_significant_mood_symptoms"] = True
                result["note"] = (
                    "علائم خلقی بالینی قابل توجهی وجود ندارد یا "
                    "همه علائم توسط اختلال اسکیزواِفکتیو توجیه می‌شوند."
                )
            else:
                # D2: manic episode history?
                d2_positive = answers.get("D2") and answers["D2"].boolean_value

                # D8: MDE history?
                d8_positive = answers.get("D8") and answers["D8"].boolean_value

                # D9: hypomanic episode history?
                d9_positive = answers.get("D9") and answers["D9"].boolean_value

                # D10: never had a full manic episode?
                d10_positive = answers.get("D10") and answers["D10"].boolean_value

                # D11: hypomanic >= 4 days?
                d11_positive = answers.get("D11") and answers["D11"].boolean_value

                # D3: not better explained by psychotic disorders (Bipolar I)
                d3_positive = answers.get("D3") and answers["D3"].boolean_value
                # D4: not substance/medical (Bipolar I)
                d4_positive = answers.get("D4") and answers["D4"].boolean_value

                # D12: clinically significant distress (Bipolar II)
                d12_positive = answers.get("D12") and answers["D12"].boolean_value
                # D13: not substance/medical (Bipolar II)
                d13_positive = answers.get("D13") and answers["D13"].boolean_value
                # D14: not better explained by psychotic disorders (Bipolar II)
                d14_positive = answers.get("D14") and answers["D14"].boolean_value

                # D17: MDE >= 2 weeks?
                d17_positive = answers.get("D17") and answers["D17"].boolean_value
                # D18: clinically significant distress (MDD)
                d18_positive = answers.get("D18") and answers["D18"].boolean_value
                # D19: not substance/medical (MDD)
                d19_positive = answers.get("D19") and answers["D19"].boolean_value

                # D20: single vs recurrent MDE
                d20_single = answers.get("D20") and answers["D20"].boolean_value

                # D22: other specified depressive: D22-D24
                d22_positive = answers.get("D22") and answers["D22"].boolean_value
                d23_positive = answers.get("D23") and answers["D23"].boolean_value
                d24_positive = answers.get("D24") and answers["D24"].boolean_value

                # Bipolar I exclusion criteria
                bipolar_i = d2_positive and d3_positive and d4_positive

                # Bipolar II exclusion criteria
                bipolar_ii = (
                    d8_positive
                    and d9_positive
                    and d10_positive
                    and d11_positive
                    and d12_positive
                    and d13_positive
                    and d14_positive
                )

                # MDD exclusion criteria
                mdd = d17_positive and d18_positive and d19_positive

                # Other specified depressive
                other_depressive = d22_positive and d23_positive and d24_positive

                # Determine diagnosis (priority: Bipolar I > Bipolar II > MDD > Other)
                diagnosis = None
                diagnosis_details = {}

                if bipolar_i:
                    diagnosis = "اختلال دوقطبی نوع ۱"
                    diagnosis_details["criteria_met"] = ["D2", "D3", "D4"]
                    # Current episode type
                    d5_positive = answers.get("D5") and answers["D5"].boolean_value
                    if d5_positive and answers.get("D6"):
                        diagnosis_details["current_episode_type"] = answers[
                            "D6"
                        ].text_value
                    else:
                        diagnosis_details["current_episode_type"] = "نامشخص"
                    # Severity
                    if answers.get("D7"):
                        diagnosis_details["severity"] = answers["D7"].text_value
                    # Chronology
                    if answers.get("D25"):
                        diagnosis_details["current"] = answers["D25"].boolean_value
                elif bipolar_ii:
                    diagnosis = "اختلال دوقطبی نوع ۲"
                    diagnosis_details["criteria_met"] = [
                        "D8",
                        "D9",
                        "D10",
                        "D11",
                        "D12",
                        "D13",
                        "D14",
                    ]
                    # Current episode type
                    d15_positive = answers.get("D15") and answers["D15"].boolean_value
                    if d15_positive:
                        diagnosis_details["current_episode_type"] = "دوره فعلی افسرده"
                    else:
                        diagnosis_details["current_episode_type"] = (
                            "دوره اخیر هیپومانیک"
                        )
                    # Severity (D16 is text)
                    if answers.get("D16"):
                        diagnosis_details["severity"] = answers["D16"].text_value
                    # Chronology
                    if answers.get("D26"):
                        diagnosis_details["current"] = answers["D26"].boolean_value
                elif mdd:
                    diagnosis = "اختلال افسردگی اساسی"
                    diagnosis_details["criteria_met"] = ["D17", "D18", "D19"]
                    # Single vs recurrent
                    diagnosis_details["episode_type"] = (
                        "تک‌دوره" if d20_single else "عودکننده"
                    )
                    # Severity (D21 is text)
                    if answers.get("D21"):
                        diagnosis_details["severity"] = answers["D21"].text_value
                    # Chronology
                    if answers.get("D27"):
                        diagnosis_details["current"] = answers["D27"].boolean_value
                elif other_depressive:
                    diagnosis = "سایر اختلالات افسردگی مشخص‌شده"
                    diagnosis_details["criteria_met"] = ["D22", "D23", "D24"]
                    # Chronology
                    if answers.get("D28"):
                        diagnosis_details["current"] = answers["D28"].boolean_value
                else:
                    diagnosis = "اختلال خلقی نامشخص"

                # Module A episode summary (referenced by Module D)
                module_a_summary = {}
                try:
                    module_a = InterviewModule.objects.get(
                        name__icontains="Mood Episodes"
                    )
                    a_answers = Answer.objects.filter(
                        interview__patient=interview.patient,
                        interview__module=module_a,
                        interview__status="completed",
                    ).order_by("-interview__completed_at")

                    if a_answers.exists():
                        latest_a = {}
                        for a in a_answers:
                            if a.question_id not in latest_a:
                                latest_a[a.question_id] = a

                        depression_ids = [
                            "A1",
                            "A2",
                            "A3",
                            "A4",
                            "A5",
                            "A6",
                            "A7",
                            "A8",
                            "A9",
                        ]
                        mania_ids = [
                            "A29",
                            "A30",
                            "A31",
                            "A32",
                            "A33",
                            "A34",
                            "A35",
                            "A36",
                            "A37",
                            "A38",
                        ]
                        hypomania_ids = [
                            "A41",
                            "A42",
                            "A43",
                            "A44",
                            "A45",
                            "A46",
                            "A47",
                            "A48",
                            "A49",
                            "A50",
                        ]

                        module_a_summary = {
                            "depression_symptoms": [
                                qid
                                for qid in depression_ids
                                if latest_a.get(qid) and latest_a[qid].boolean_value
                            ],
                            "mania_symptoms": [
                                qid
                                for qid in mania_ids
                                if latest_a.get(qid) and latest_a[qid].boolean_value
                            ],
                            "hypomania_symptoms": [
                                qid
                                for qid in hypomania_ids
                                if latest_a.get(qid) and latest_a[qid].boolean_value
                            ],
                        }
                except InterviewModule.DoesNotExist:
                    pass

                result.update(
                    {
                        "diagnosis": diagnosis,
                        "details": diagnosis_details,
                        "criteria_summary": {
                            "bipolar_i": {
                                "met": bipolar_i,
                                "criteria_positive": (
                                    ["D2", "D3", "D4"] if bipolar_i else []
                                ),
                            },
                            "bipolar_ii": {
                                "met": bipolar_ii,
                                "criteria_positive": (
                                    ["D8", "D9", "D10", "D11", "D12", "D13", "D14"]
                                    if bipolar_ii
                                    else []
                                ),
                            },
                            "mdd": {
                                "met": mdd,
                                "criteria_positive": (
                                    ["D17", "D18", "D19"] if mdd else []
                                ),
                            },
                            "other_depressive": {
                                "met": other_depressive,
                                "criteria_positive": (
                                    ["D22", "D23", "D24"] if other_depressive else []
                                ),
                            },
                        },
                        "module_a_episodes": module_a_summary,
                    }
                )

        elif "Psychotic" in interview.module.name:
            answers = {a.question.id: a for a in interview.answers.all()}

            delusion_ids = [
                "B1",
                "B2",
                "B3",
                "B4",
                "B5",
                "B6",
                "B7",
                "B8",
                "B9",
                "B10",
                "B11",
            ]
            hallucination_ids = ["B12", "B13", "B14", "B15", "B16", "B17"]
            disorganized_ids = ["B18", "B19"]
            catatonic_ids = ["B20"]
            negative_ids = ["B21", "B22"]

            delusions_present = [
                qid
                for qid in delusion_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            hallucinations_present = [
                qid
                for qid in hallucination_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            disorganized_present = [
                qid
                for qid in disorganized_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            catatonic_present = [
                qid
                for qid in catatonic_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            negative_present = [
                qid
                for qid in negative_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]

            due_to_medical = answers.get("B23") and answers["B23"].boolean_value
            due_to_substance = answers.get("B24") and answers["B24"].boolean_value

            result.update(
                {
                    "psychotic_symptoms": {
                        "delusions": {
                            "present": len(delusions_present) > 0,
                            "count": len(delusions_present),
                            "items": delusions_present,
                        },
                        "hallucinations": {
                            "present": len(hallucinations_present) > 0,
                            "count": len(hallucinations_present),
                            "items": hallucinations_present,
                        },
                        "disorganized_speech_or_behavior": {
                            "present": len(disorganized_present) > 0,
                            "items": disorganized_present,
                        },
                        "catatonic_behavior": {
                            "present": len(catatonic_present) > 0,
                            "items": catatonic_present,
                        },
                        "negative_symptoms": {
                            "present": len(negative_present) > 0,
                            "items": negative_present,
                        },
                    },
                    "exclusion_factors": {
                        "due_to_medical_condition": due_to_medical,
                        "due_to_substance": due_to_substance,
                    },
                    "note": "This is a symptom profile. Diagnosis (Schizophrenia, Schizoaffective, etc.) requires Module C — Differential Diagnosis of Psychotic Disorders.",
                }
            )

        return result


@extend_schema_view(
    post=interview_pause_schema,
)
class InterviewPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"}, status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != "in_progress":
            return Response(
                {"error": "Interview is not in progress"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interview.status = "paused"
        interview.save()

        return Response({"message": "Interview paused successfully"})


@extend_schema_view(
    post=interview_resume_schema,
)
class InterviewResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"}, status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != "paused":
            return Response(
                {"error": "Interview is not paused"}, status=status.HTTP_400_BAD_REQUEST
            )

        interview.status = "in_progress"
        interview.save()

        return Response(
            {
                "message": "Interview resumed successfully",
                "current_question": (
                    QuestionListSerializer(interview.current_question).data
                    if interview.current_question
                    else None
                ),
            }
        )


@extend_schema_view(
    get=interview_summary_schema,
)
class InterviewSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        interview = get_object_or_404(Interview, id=id)

        if interview.clinician != request.user:
            return Response(
                {"error": "You don't have permission"}, status=status.HTTP_403_FORBIDDEN
            )

        if interview.status != "completed":
            return Response(
                {"error": "Interview is not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        progress_view = InterviewProgressView()
        diagnosis = progress_view._calculate_diagnosis(interview)

        return Response(
            {
                "interview_id": str(interview.id),
                "diagnosis_result": diagnosis,
                "completed_questions": interview.answers.count(),
                "total_questions": interview.module.questions.count(),
                "completion_percentage": (
                    (interview.answers.count() / interview.module.questions.count())
                    * 100
                    if interview.module.questions.count() > 0
                    else 0
                ),
                "duration": self._calculate_duration(interview),
            }
        )

    def _calculate_duration(self, interview):
        """Calculate interview duration in minutes"""
        if interview.started_at and interview.completed_at:
            duration = interview.completed_at - interview.started_at
            return duration.total_seconds() / 60  # Return in minutes
        return None


# ============================================================
# 📝 ANSWER VIEWS
# ============================================================


class InterviewAnswerListView(generics.ListAPIView):
    """List answers for a specific interview"""

    permission_classes = [IsAuthenticated]
    serializer_class = AnswerListSerializer

    def get_queryset(self):
        interview_id = self.kwargs["interview_id"]
        return Answer.objects.filter(interview_id=interview_id)


class AnswerDetailView(generics.RetrieveAPIView):
    """Retrieve a specific answer"""

    permission_classes = [IsAuthenticated]
    serializer_class = AnswerDetailSerializer
    queryset = Answer.objects.all()
    lookup_field = "id"


# ============================================================
# 🔄 JUMP RULE VIEWS
# ============================================================


class JumpRuleListView(generics.ListAPIView):
    """List all jump rules"""

    permission_classes = [IsAuthenticated]
    serializer_class = JumpRuleListSerializer
    queryset = JumpRule.objects.all()


class JumpRuleDetailView(generics.RetrieveAPIView):
    """Retrieve a specific jump rule"""

    permission_classes = [IsAuthenticated]
    serializer_class = JumpRuleDetailSerializer
    queryset = JumpRule.objects.all()
    lookup_field = "id"
