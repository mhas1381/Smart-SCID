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

        elif "Substance Use" in interview.module.name:
            answers = {a.question.id: a for a in interview.answers.all()}

            # Phase 1: Alcohol Use Disorder (E1-E13)
            e1_positive = answers.get("E1") and answers["E1"].boolean_value

            alcohol_criteria_ids = ["E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12"]
            alcohol_met = [
                qid for qid in alcohol_criteria_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            alcohol_count = len(alcohol_met)

            if alcohol_count >= 6:
                alcohol_severity = "شدید"
            elif alcohol_count >= 4:
                alcohol_severity = "متوسط"
            elif alcohol_count >= 2:
                alcohol_severity = "خفیف"
            else:
                alcohol_severity = None

            # Phase 2: Nonalcohol Substance Screening (E14-E22)
            e14_positive = answers.get("E14") and answers["E14"].boolean_value

            substance_screens = {
                "E15": "آرامبخش / خواب‌آور / ضداضطراب",
                "E16": "شاهدانه (ماریجوانا)",
                "E17": "محرک‌ها (شیشه / کوکائین)",
                "E18": "مواد افیونی (هروئین / مسکن‌ها)",
                "E19": "فنسیکلیدین (PCP / کتامین)",
                "E20": "توهم‌زاها (LSD / اکستازی)",
                "E21": "مواد استنشاقی",
                "E22": "سایر مواد",
            }

            substances_used = [
                substance_screens[qid]
                for qid in substance_screens
                if answers.get(qid) and answers[qid].boolean_value
            ]

            # Phase 3: Substance Use Disorder Criteria (E38-E48)
            e37_text = answers["E37"].text_value if answers.get("E37") else None

            substance_criteria_ids = [
                "E38", "E39", "E40", "E41", "E42",
                "E43", "E44", "E45", "E46", "E47", "E48",
            ]
            substance_met = [
                qid for qid in substance_criteria_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            substance_count = len(substance_met)

            if substance_count >= 6:
                substance_severity = "شدید"
            elif substance_count >= 4:
                substance_severity = "متوسط"
            elif substance_count >= 2:
                substance_severity = "خفیف"
            else:
                substance_severity = None

            # Build result
            result.update({
                "alcohol": {
                    "diagnosed": alcohol_count >= 2 and e1_positive,
                    "symptoms_counted": alcohol_count,
                    "required_symptoms_count": 2,
                    "severity": alcohol_severity if alcohol_count >= 2 and e1_positive else None,
                    "criteria_met": alcohol_met if alcohol_count >= 2 and e1_positive else [],
                },
                "substances_screened": {
                    "any_substance_used": e14_positive,
                    "substances_reported": substances_used,
                },
                "substance_use_disorder": {
                    "diagnosed": substance_count >= 2 and e14_positive,
                    "primary_substance": e37_text,
                    "symptoms_counted": substance_count,
                    "required_symptoms_count": 2,
                    "severity": substance_severity if substance_count >= 2 and e14_positive else None,
                    "criteria_met": substance_met if substance_count >= 2 and e14_positive else [],
                },
            })

        elif "Anxiety Disorders" in interview.module.name:
            # ================================================================
            # MODULE F — ANXIETY DISORDERS
            # ================================================================
            # 4 disorders: Panic, Agoraphobia, Social Anxiety, GAD
            # Each has: gate, criteria, exclusions, severity, chronology

            answers = {a.question.id: a for a in interview.answers.all()}

            # ---- Panic Disorder (F1-F7) ----
            f1_positive = answers.get("F1") and answers["F1"].boolean_value
            f2_positive = answers.get("F2") and answers["F2"].boolean_value
            f3_no_substance = answers.get("F3") and answers["F3"].boolean_value
            f4_no_medical = answers.get("F4") and answers["F4"].boolean_value
            f5_no_other = answers.get("F5") and answers["F5"].boolean_value

            panic_diagnosed = (
                f1_positive
                and f2_positive
                and f3_no_substance
                and f4_no_medical
                and f5_no_other
            )
            panic_severity = None
            if answers.get("F6"):
                panic_severity = answers["F6"].text_value
            panic_current = None
            if answers.get("F7"):
                panic_current = answers["F7"].text_value

            result.update({
                "panic_disorder": {
                    "diagnosed": panic_diagnosed,
                    "severity": panic_severity,
                    "chronology": panic_current,
                },
            })

            # ---- Agoraphobia (F8-F19) ----
            f8_positive = answers.get("F8") and answers["F8"].boolean_value
            situation_ids = ["F9", "F10", "F11", "F12", "F13"]
            situations_met = [
                qid for qid in situation_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            f14_avoidance = answers.get("F14") and answers["F14"].boolean_value
            f15_disproportionate = answers.get("F15") and answers["F15"].boolean_value
            f16_no_substance = answers.get("F16") and answers["F16"].boolean_value
            f17_no_other = answers.get("F17") and answers["F17"].boolean_value

            agoraphobia_diagnosed = (
                f8_positive
                and len(situations_met) >= 2
                and f14_avoidance
                and f15_disproportionate
                and f16_no_substance
                and f17_no_other
            )
            agoraphobia_severity = None
            if answers.get("F18"):
                agoraphobia_severity = answers["F18"].text_value
            agoraphobia_current = None
            if answers.get("F19"):
                agoraphobia_current = answers["F19"].text_value

            result.update({
                "agoraphobia": {
                    "diagnosed": agoraphobia_diagnosed,
                    "situations_count": len(situations_met),
                    "situations_met": situations_met,
                    "severity": agoraphobia_severity,
                    "chronology": agoraphobia_current,
                },
            })

            # ---- Social Anxiety Disorder (F20-F28) ----
            f20_positive = answers.get("F20") and answers["F20"].boolean_value
            f21_negative_eval = answers.get("F21") and answers["F21"].boolean_value
            f22_persistent_fear = answers.get("F22") and answers["F22"].boolean_value
            f23_avoidance = answers.get("F23") and answers["F23"].boolean_value
            f24_disproportionate = answers.get("F24") and answers["F24"].boolean_value
            f25_no_substance = answers.get("F25") and answers["F25"].boolean_value
            f26_no_other = answers.get("F26") and answers["F26"].boolean_value

            social_anxiety_diagnosed = (
                f20_positive
                and f21_negative_eval
                and f22_persistent_fear
                and f23_avoidance
                and f24_disproportionate
                and f25_no_substance
                and f26_no_other
            )
            social_anxiety_severity = None
            if answers.get("F27"):
                social_anxiety_severity = answers["F27"].text_value
            social_anxiety_current = None
            if answers.get("F28"):
                social_anxiety_current = answers["F28"].text_value

            result.update({
                "social_anxiety": {
                    "diagnosed": social_anxiety_diagnosed,
                    "severity": social_anxiety_severity,
                    "chronology": social_anxiety_current,
                },
            })

            # ---- Generalized Anxiety Disorder (F29-F40) ----
            f29_positive = answers.get("F29") and answers["F29"].boolean_value
            f30_control = answers.get("F30") and answers["F30"].boolean_value
            gad_symptom_ids = ["F31", "F32", "F33", "F34", "F35", "F36"]
            gad_symptoms_met = [
                qid for qid in gad_symptom_ids
                if answers.get(qid) and answers[qid].boolean_value
            ]
            f37_no_substance = answers.get("F37") and answers["F37"].boolean_value
            f38_no_other = answers.get("F38") and answers["F38"].boolean_value

            gad_diagnosed = (
                f29_positive
                and f30_control
                and len(gad_symptoms_met) >= 3
                and f37_no_substance
                and f38_no_other
            )
            gad_severity = None
            if answers.get("F39"):
                gad_severity = answers["F39"].text_value
            gad_current = None
            if answers.get("F40"):
                gad_current = answers["F40"].text_value

            result.update({
                "generalized_anxiety": {
                    "diagnosed": gad_diagnosed,
                    "associated_symptoms_count": len(gad_symptoms_met),
                    "associated_symptoms_met": gad_symptoms_met,
                    "severity": gad_severity,
                    "chronology": gad_current,
                },
            })

        elif "Obsessive-Compulsive" in interview.module.name:
            # ================================================================
            # MODULE G — OBSESSIVE-COMPULSIVE AND RELATED DISORDERS
            # ================================================================
            # 5 disorders: OCD, BDD, Hoarding, Trichotillomania, Excoriation
            # Each has: gate, criteria, exclusions, severity, chronology

            answers = {a.question.id: a for a in interview.answers.all()}

            # ---- OCD (G1-G9) ----
            g1_positive = answers.get("G1") and answers["G1"].boolean_value
            g2_positive = answers.get("G2") and answers["G2"].boolean_value
            g3_positive = answers.get("G3") and answers["G3"].boolean_value
            g4_positive = answers.get("G4") and answers["G4"].boolean_value
            g5_positive = answers.get("G5") and answers["G5"].boolean_value
            g6_no_substance = answers.get("G6") and answers["G6"].boolean_value
            g7_no_other = answers.get("G7") and answers["G7"].boolean_value

            ocd_criteria_met = [
                c for c, v in {
                    "G2": g2_positive, "G3": g3_positive,
                    "G4": g4_positive, "G5": g5_positive,
                }.items() if v
            ]

            ocd_diagnosed = (
                g1_positive
                and g2_positive
                and g3_positive
                and g4_positive
                and g5_positive
                and g6_no_substance
                and g7_no_other
            )

            ocd_severity = None
            ocd_current = None
            if ocd_diagnosed:
                g8_answer = answers.get("G8")
                if g8_answer and g8_answer.text_value:
                    ocd_severity = g8_answer.text_value
                g9_answer = answers.get("G9")
                if g9_answer and g9_answer.text_value:
                    ocd_current = g9_answer.text_value

            result.update({
                "ocd": {
                    "diagnosed": ocd_diagnosed,
                    "criteria_met": ocd_criteria_met,
                    "severity": ocd_severity,
                    "chronology": ocd_current,
                },
            })

            # ---- BDD (G10-G15) ----
            g10_positive = answers.get("G10") and answers["G10"].boolean_value
            g11_positive = answers.get("G11") and answers["G11"].boolean_value
            g12_positive = answers.get("G12") and answers["G12"].boolean_value
            g13_no_eating = answers.get("G13") and answers["G13"].boolean_value

            bdd_diagnosed = (
                g10_positive
                and g11_positive
                and g12_positive
                and g13_no_eating
            )

            bdd_severity = None
            bdd_current = None
            if bdd_diagnosed:
                g14_answer = answers.get("G14")
                if g14_answer and g14_answer.text_value:
                    bdd_severity = g14_answer.text_value
                g15_answer = answers.get("G15")
                if g15_answer and g15_answer.text_value:
                    bdd_current = g15_answer.text_value

            result.update({
                "body_dysmorphic": {
                    "diagnosed": bdd_diagnosed,
                    "severity": bdd_severity,
                    "chronology": bdd_current,
                },
            })

            # ---- Hoarding (G16-G22) ----
            g16_positive = answers.get("G16") and answers["G16"].boolean_value
            g17_positive = answers.get("G17") and answers["G17"].boolean_value
            g18_positive = answers.get("G18") and answers["G18"].boolean_value
            g19_positive = answers.get("G19") and answers["G19"].boolean_value
            g20_no_medical = answers.get("G20") and answers["G20"].boolean_value

            hoarding_diagnosed = (
                g16_positive
                and g17_positive
                and (g18_positive or g19_positive)
                and g20_no_medical
            )

            hoarding_severity = None
            hoarding_current = None
            if hoarding_diagnosed:
                g21_answer = answers.get("G21")
                if g21_answer and g21_answer.text_value:
                    hoarding_severity = g21_answer.text_value
                g22_answer = answers.get("G22")
                if g22_answer and g22_answer.text_value:
                    hoarding_current = g22_answer.text_value

            result.update({
                "hoarding": {
                    "diagnosed": hoarding_diagnosed,
                    "severity": hoarding_severity,
                    "chronology": hoarding_current,
                },
            })

            # ---- Trichotillomania (G23-G28) ----
            g23_positive = answers.get("G23") and answers["G23"].boolean_value
            g24_positive = answers.get("G24") and answers["G24"].boolean_value
            g25_positive = answers.get("G25") and answers["G25"].boolean_value
            g26_no_medical = answers.get("G26") and answers["G26"].boolean_value

            trich_diagnosed = (
                g23_positive
                and g24_positive
                and g25_positive
                and g26_no_medical
            )

            trich_severity = None
            trich_current = None
            if trich_diagnosed:
                g27_answer = answers.get("G27")
                if g27_answer and g27_answer.text_value:
                    trich_severity = g27_answer.text_value
                g28_answer = answers.get("G28")
                if g28_answer and g28_answer.text_value:
                    trich_current = g28_answer.text_value

            result.update({
                "trichotillomania": {
                    "diagnosed": trich_diagnosed,
                    "severity": trich_severity,
                    "chronology": trich_current,
                },
            })

            # ---- Excoriation (G29-G34) ----
            g29_positive = answers.get("G29") and answers["G29"].boolean_value
            g30_positive = answers.get("G30") and answers["G30"].boolean_value
            g31_positive = answers.get("G31") and answers["G31"].boolean_value
            g32_no_medical = answers.get("G32") and answers["G32"].boolean_value

            excor_diagnosed = (
                g29_positive
                and g30_positive
                and g31_positive
                and g32_no_medical
            )

            excor_severity = None
            excor_current = None
            if excor_diagnosed:
                g33_answer = answers.get("G33")
                if g33_answer and g33_answer.text_value:
                    excor_severity = g33_answer.text_value
                g34_answer = answers.get("G34")
                if g34_answer and g34_answer.text_value:
                    excor_current = g34_answer.text_value

            result.update({
                "excoriation": {
                    "diagnosed": excor_diagnosed,
                    "severity": excor_severity,
                    "chronology": excor_current,
                },
            })

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
