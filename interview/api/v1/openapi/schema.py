"""
OpenAPI schema definitions for interviews API v1.
"""

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    inline_serializer,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers


# ============================================================
# 📋 MODULE SCHEMAS
# ============================================================

module_list_schema = extend_schema(
    summary="📋 List Interview Modules",
    tags=["📋 Interview"],
    description="""
Retrieve all active interview modules.

📋 Each module contains:
- Name and description
- Version number
- Question count

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="ModuleListResponse",
            fields={
                "count": serializers.IntegerField(),
                "next": serializers.CharField(allow_null=True),
                "previous": serializers.CharField(allow_null=True),
                "results": serializers.ListField(
                    child=inline_serializer(
                        name="ModuleItem",
                        fields={
                            "id": serializers.IntegerField(),
                            "name": serializers.CharField(),
                            "description": serializers.CharField(),
                            "version": serializers.CharField(),
                            "is_active": serializers.BooleanField(),
                            "order": serializers.IntegerField(),
                            "question_count": serializers.IntegerField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📋 Module List Response",
            value={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": 1,
                        "name": "Module A - Mood Episodes",
                        "description": "ارزیابی دوره‌های خلقی شامل افسردگی اساسی، مانیا و هیپومانیا بر اساس DSM-5",
                        "version": "1.0",
                        "is_active": True,
                        "order": 1,
                        "question_count": 53,
                    }
                ],
            },
            response_only=True,
        ),
    ],
)


module_detail_schema = extend_schema(
    summary="📄 Get Module Details",
    tags=["📋 Interview"],
    description="""
Retrieve details of a specific interview module.

📋 Returns:
- Module information
- List of all questions in the module

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="ModuleDetailResponse",
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
                "description": serializers.CharField(),
                "version": serializers.CharField(),
                "is_active": serializers.BooleanField(),
                "order": serializers.IntegerField(),
                "question_count": serializers.IntegerField(),
                "questions": serializers.ListField(
                    child=inline_serializer(
                        name="ModuleQuestionItem",
                        fields={
                            "id": serializers.CharField(),
                            "text": serializers.CharField(),
                            "question_type": serializers.CharField(),
                            "is_criteria": serializers.BooleanField(),
                            "criteria_number": serializers.CharField(),
                            "order": serializers.IntegerField(),
                            "is_required": serializers.BooleanField(),
                            "has_jump_logic": serializers.BooleanField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📄 Module Detail Response",
            value={
                "id": 1,
                "name": "Module A - Mood Episodes",
                "description": "ارزیابی دوره‌های خلقی شامل افسردگی اساسی، مانیا و هیپومانیا بر اساس DSM-5",
                "version": "1.0",
                "is_active": True,
                "order": 1,
                "question_count": 53,
                "questions": [
                    {
                        "id": "A1",
                        "text": "در طول بدترین دوره دو هفته‌ای، آیا احساس افسردگی، غم‌گینی یا بی‌حالی داشتید؟",
                        "question_type": "boolean",
                        "is_criteria": True,
                        "criteria_number": "1",
                        "order": 1,
                        "is_required": True,
                        "has_jump_logic": True,
                    },
                    {
                        "id": "A2",
                        "text": "در طول بدترین دوره دو هفته‌ای، آیا به طور قابل توجهی علاقه یا لذت را در فعالیت‌هایی که معمولاً لذت‌بخش بودند، از دست دادید؟",
                        "question_type": "boolean",
                        "is_criteria": True,
                        "criteria_number": "2",
                        "order": 2,
                        "is_required": True,
                        "has_jump_logic": False,
                    },
                ],
            },
            response_only=True,
        ),
    ],
)


# ============================================================
# ❓ QUESTION SCHEMAS
# ============================================================

question_list_schema = extend_schema(
    summary="❓ List Interview Questions",
    tags=["📋 Interview"],
    description="""
Retrieve all questions for a specific module.

🔸 Optional filter: `?module_id={id}`

📋 Each question includes:
- ID (e.g., A1, A2)
- Question text in Persian
- Question type (boolean, multiple_choice, text, number, date, rating)
- Criteria information (if applicable)
- Order in module

🔐 JWT authentication required
    """,
    parameters=[
        OpenApiParameter(
            name="module_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter questions by module ID",
            required=False,
        ),
    ],
    responses={
        200: inline_serializer(
            name="QuestionListResponse",
            fields={
                "count": serializers.IntegerField(),
                "next": serializers.CharField(allow_null=True),
                "previous": serializers.CharField(allow_null=True),
                "results": serializers.ListField(
                    child=inline_serializer(
                        name="QuestionItem",
                        fields={
                            "id": serializers.CharField(),
                            "text": serializers.CharField(),
                            "question_type": serializers.CharField(),
                            "is_criteria": serializers.BooleanField(),
                            "criteria_number": serializers.CharField(),
                            "order": serializers.IntegerField(),
                            "is_required": serializers.BooleanField(),
                            "has_jump_logic": serializers.BooleanField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "❓ Question List Response - Module A",
            value={
                "count": 53,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": "A1",
                        "text": "در طول بدترین دوره دو هفته‌ای، آیا احساس افسردگی، غم‌گینی یا بی‌حالی داشتید؟",
                        "question_type": "boolean",
                        "is_criteria": True,
                        "criteria_number": "1",
                        "order": 1,
                        "is_required": True,
                        "has_jump_logic": True,
                    },
                    {
                        "id": "A2",
                        "text": "در طول بدترین دوره دو هفته‌ای، آیا به طور قابل توجهی علاقه یا لذت را در فعالیت‌هایی که معمولاً لذت‌بخش بودند، از دست دادید؟",
                        "question_type": "boolean",
                        "is_criteria": True,
                        "criteria_number": "2",
                        "order": 2,
                        "is_required": True,
                        "has_jump_logic": False,
                    },
                    {
                        "id": "A3",
                        "text": "در طول بدترین دوره دو هفته‌ای، آیا به طور قابل توجهی وزن خود را کاهش دادید یا اشتها را از دست دادید؟",
                        "question_type": "boolean",
                        "is_criteria": True,
                        "criteria_number": "3",
                        "order": 3,
                        "is_required": True,
                        "has_jump_logic": False,
                    },
                ],
            },
            response_only=True,
        ),
    ],
)


question_detail_schema = extend_schema(
    summary="📄 Get Question Details",
    tags=["📋 Interview"],
    description="""
Retrieve details of a specific question.

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="QuestionDetailResponse",
            fields={
                "id": serializers.CharField(),
                "module": serializers.IntegerField(),
                "text": serializers.CharField(),
                "question_type": serializers.CharField(),
                "is_criteria": serializers.BooleanField(),
                "criteria_number": serializers.CharField(),
                "order": serializers.IntegerField(),
                "is_required": serializers.BooleanField(),
                "has_jump_logic": serializers.BooleanField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📄 Question Detail Response - A1",
            value={
                "id": "A1",
                "module": 1,
                "text": "در طول بدترین دوره دو هفته‌ای، آیا احساس افسردگی، غم‌گینی یا بی‌حالی داشتید؟",
                "question_type": "boolean",
                "is_criteria": True,
                "criteria_number": "1",
                "order": 1,
                "is_required": True,
                "has_jump_logic": True,
            },
            response_only=True,
        ),
    ],
)


# ============================================================
# 🎬 INTERVIEW SCHEMAS
# ============================================================

interview_list_schema = extend_schema(
    summary="📋 List Interviews",
    tags=["📋 Interview"],
    description="""
Retrieve all interviews for the authenticated clinician.

🔐 JWT authentication required
👤 Only returns interviews conducted by the current clinician
    """,
    responses={
        200: inline_serializer(
            name="InterviewListResponse",
            fields={
                "count": serializers.IntegerField(),
                "next": serializers.CharField(allow_null=True),
                "previous": serializers.CharField(allow_null=True),
                "results": serializers.ListField(
                    child=inline_serializer(
                        name="InterviewItem",
                        fields={
                            "id": serializers.CharField(),
                            "patient": serializers.CharField(),
                            "patient_name": serializers.CharField(),
                            "clinician": serializers.IntegerField(),
                            "clinician_name": serializers.CharField(),
                            "module": serializers.IntegerField(),
                            "module_name": serializers.CharField(),
                            "status": serializers.CharField(),
                            "started_at": serializers.CharField(),
                            "completed_at": serializers.CharField(allow_null=True),
                            "answer_count": serializers.IntegerField(),
                        },
                    )
                ),
            },
        ),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📋 Interview List Response",
            value={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "patient": "550e8400-e29b-41d4-a716-446655440000",
                        "patient_name": "علی محمدی",
                        "clinician": 1,
                        "clinician_name": "دکتر احمد رضایی",
                        "module": 1,
                        "module_name": "Module A - Mood Episodes",
                        "status": "completed",
                        "started_at": "2026-06-21T10:30:00Z",
                        "completed_at": "2026-06-21T11:45:00Z",
                        "answer_count": 53,
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "patient": "550e8400-e29b-41d4-a716-446655440003",
                        "patient_name": "سارا احمدی",
                        "clinician": 1,
                        "clinician_name": "دکتر احمد رضایی",
                        "module": 1,
                        "module_name": "Module A - Mood Episodes",
                        "status": "in_progress",
                        "started_at": "2026-06-21T14:00:00Z",
                        "completed_at": None,
                        "answer_count": 12,
                    },
                ],
            },
            response_only=True,
        ),
    ],
)


interview_detail_schema = extend_schema(
    summary="📄 Get Interview Details",
    tags=["📋 Interview"],
    description="""
Get detailed information about a specific interview.

📋 Returns:
- Patient and clinician information
- Module details
- All answers
- Current question (if in progress)

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="InterviewDetailResponse",
            fields={
                "id": serializers.CharField(),
                "patient": serializers.CharField(),
                "patient_name": serializers.CharField(),
                "clinician": serializers.IntegerField(),
                "clinician_name": serializers.CharField(),
                "module": serializers.IntegerField(),
                "module_name": serializers.CharField(),
                "status": serializers.CharField(),
                "started_at": serializers.CharField(),
                "completed_at": serializers.CharField(allow_null=True),
                "current_question": serializers.DictField(allow_null=True),
                "answers": serializers.ListField(),
                "answer_count": serializers.IntegerField(),
            },
        ),
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📄 Interview Detail Response - In Progress",
            value={
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "patient": "550e8400-e29b-41d4-a716-446655440003",
                "patient_name": "سارا احمدی",
                "clinician": 1,
                "clinician_name": "دکتر احمد رضایی",
                "module": 1,
                "module_name": "Module A - Mood Episodes",
                "status": "in_progress",
                "started_at": "2026-06-21T14:00:00Z",
                "completed_at": None,
                "current_question": {
                    "id": "A15",
                    "text": "آیا بیمار در حال حاضر دچار اختلال افسردگی اساسی است؟",
                    "question_type": "boolean",
                },
                "answers": [
                    {
                        "question_id": "A1",
                        "question_text": "در طول بدترین دوره دو هفته‌ای، آیا احساس افسردگی، غم‌گینی یا بی‌حالی داشتید؟",
                        "answer_type": "boolean",
                        "value": {"boolean": True},
                    },
                    {
                        "question_id": "A2",
                        "question_text": "در طول بدترین دوره دو هفته‌ای، آیا به طور قابل توجهی علاقه یا لذت را در فعالیت‌هایی که معمولاً لذت‌بخش بودند، از دست دادید؟",
                        "answer_type": "boolean",
                        "value": {"boolean": True},
                    },
                ],
                "answer_count": 12,
            },
            response_only=True,
        ),
    ],
)


interview_start_schema = extend_schema(
    summary="🎬 Start New Interview",
    tags=["📋 Interview"],
    description="""
Start a new interview session for a patient.

✅ Required:
- patient_id: UUID of the patient
- module_id: ID of the module to use

📋 Process:
1. Creates a new interview session
2. Sets the first question as current
3. Returns the interview with current question

🔐 JWT authentication required
    """,
    request=inline_serializer(
        name="StartInterviewRequest",
        fields={
            "patient_id": serializers.CharField(required=True),
            "module_id": serializers.IntegerField(required=True),
        },
    ),
    responses={
        201: inline_serializer(
            name="StartInterviewResponse",
            fields={
                "id": serializers.CharField(),
                "patient": serializers.CharField(),
                "patient_name": serializers.CharField(),
                "clinician": serializers.IntegerField(),
                "clinician_name": serializers.CharField(),
                "module": serializers.IntegerField(),
                "module_name": serializers.CharField(),
                "status": serializers.CharField(),
                "started_at": serializers.CharField(),
                "completed_at": serializers.CharField(allow_null=True),
                "current_question": serializers.DictField(),
                "answer_count": serializers.IntegerField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Start Interview Request",
            value={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "module_id": 1,
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Start Interview Response",
            value={
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "patient": "550e8400-e29b-41d4-a716-446655440000",
                "patient_name": "علی محمدی",
                "clinician": 1,
                "clinician_name": "دکتر احمد رضایی",
                "module": 1,
                "module_name": "Module A - Mood Episodes",
                "status": "in_progress",
                "started_at": "2026-06-21T10:30:00Z",
                "completed_at": None,
                "current_question": {
                    "id": "A1",
                    "text": "در طول بدترین دوره دو هفته‌ای، آیا احساس افسردگی، غم‌گینی یا بی‌حالی داشتید؟",
                    "question_type": "boolean",
                    "is_criteria": True,
                    "criteria_number": "1",
                },
                "answer_count": 0,
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Patient Not Found",
            value={
                "patient_id": ["Patient not found"],
            },
            response_only=True,
        ),
        OpenApiExample(
            "❌ Module Not Active",
            value={
                "module_id": ["Module is not active"],
            },
            response_only=True,
        ),
    ],
)


interview_progress_schema = extend_schema(
    summary="📝 Submit Answer & Get Next Question",
    tags=["📋 Interview"],
    description="""
Submit answer for a question and get the next question.

✅ Required:
- question_id: ID of the question being answered
- answer_value: The answer value (structure depends on question type)
- answer_type: Type of answer (boolean, multiple_choice, text, number, date, rating)

🔸 Optional:
- notes: Clinician notes for this answer

📋 For boolean questions: {"boolean": true/false}
📋 For multiple_choice: {"choice": "selected_option"}
📋 For text: {"text": "user input"}
📋 For number/rating: {"number": 5}

🔐 JWT authentication required
    """,
    request=inline_serializer(
        name="ProgressInterviewRequest",
        fields={
            "question_id": serializers.CharField(required=True),
            "answer_value": serializers.JSONField(required=True),
            "answer_type": serializers.CharField(required=True),
            "notes": serializers.CharField(required=False, allow_blank=True),
        },
    ),
    responses={
        200: inline_serializer(
            name="ProgressInterviewResponse",
            fields={
                "current_question": serializers.DictField(allow_null=True),
                "has_next": serializers.BooleanField(),
                "interview_status": serializers.CharField(),
                "answered_questions": serializers.IntegerField(),
                "total_questions": serializers.IntegerField(),
                "diagnosis_result": serializers.DictField(required=False),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📤 Submit Boolean Answer - Yes",
            value={
                "question_id": "A1",
                "answer_value": {"boolean": True},
                "answer_type": "boolean",
                "notes": "بیمار تأیید کرد که در دو هفته اخیر احساس افسردگی داشته است",
            },
            request_only=True,
        ),
        OpenApiExample(
            "📤 Submit Boolean Answer - No",
            value={
                "question_id": "A2",
                "answer_value": {"boolean": False},
                "answer_type": "boolean",
            },
            request_only=True,
        ),
        OpenApiExample(
            "📤 Submit Text Answer",
            value={
                "question_id": "A15",
                "answer_value": {"text": "بیمار از ۳ سال پیش دچار بی‌خوابی و کاهش انرژی شده"},
                "answer_type": "text",
                "notes": "بیمار بیان کرد که این علائم بعد از مرگ پدرش شروع شده",
            },
            request_only=True,
        ),
        OpenApiExample(
            "✅ Progress Response - Has Next Question",
            value={
                "current_question": {
                    "id": "A2",
                    "text": "در طول بدترین دوره دو هفته‌ای، آیا به طور قابل توجهی علاقه یا لذت را در فعالیت‌هایی که معمولاً لذت‌بخش بودند، از دست دادید؟",
                    "question_type": "boolean",
                },
                "has_next": True,
                "interview_status": "in_progress",
                "answered_questions": 1,
                "total_questions": 53,
            },
            response_only=True,
        ),
        OpenApiExample(
            "✅ Progress Response - With Jump Logic",
            value={
                "current_question": {
                    "id": "A3",
                    "text": "در طول بدترین دوره دو هفته‌ای، آیا به طور قابل توجهی وزن خود را کاهش دادید یا اشتها را از دست دادید؟",
                    "question_type": "boolean",
                },
                "has_next": True,
                "interview_status": "in_progress",
                "answered_questions": 1,
                "total_questions": 53,
            },
            response_only=True,
        ),
        OpenApiExample(
            "✅ Progress Response - Interview Completed",
            value={
                "current_question": None,
                "has_next": False,
                "interview_status": "completed",
                "answered_questions": 53,
                "total_questions": 53,
                "diagnosis_result": {
                    "module": "Module A - Mood Episodes",
                    "completed_at": "2026-06-21T11:45:00Z",
                    "depression": {
                        "diagnosed": True,
                        "symptoms_counted": 6,
                        "required_symptoms_count": 5,
                        "criteria_met": ["A1", "A2", "A4", "A5", "A7", "A9"],
                    },
                    "mania": {
                        "diagnosed": False,
                        "symptoms_counted": 1,
                        "required_symptoms_count": 4,
                        "criteria_met": ["A29"],
                    },
                    "hypomania": {
                        "diagnosed": False,
                        "symptoms_counted": 0,
                        "required_symptoms_count": 4,
                        "criteria_met": [],
                    },
                },
            },
            response_only=True,
        ),
    ],
)


interview_pause_schema = extend_schema(
    summary="⏸️ Pause Interview",
    tags=["📋 Interview"],
    description="""
Pause an ongoing interview.

📋 The interview status changes from 'in_progress' to 'paused'.
📋 Can be resumed later using the resume endpoint.

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="PauseInterviewResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "✅ Pause Response",
            value={
                "message": "مصاحبه با موفقیت متوقف شد",
            },
            response_only=True,
        ),
    ],
)


interview_resume_schema = extend_schema(
    summary="▶️ Resume Interview",
    tags=["📋 Interview"],
    description="""
Resume a paused interview.

📋 The interview status changes from 'paused' to 'in_progress'.
📋 Returns the current question to continue from.

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="ResumeInterviewResponse",
            fields={
                "message": serializers.CharField(),
                "current_question": serializers.DictField(allow_null=True),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "✅ Resume Response",
            value={
                "message": "مصاحبه با موفقیت ادامه یافت",
                "current_question": {
                    "id": "A15",
                    "text": "آیا بیمار در حال حاضر دچار اختلال افسردگی اساسی است؟",
                    "question_type": "boolean",
                },
            },
            response_only=True,
        ),
    ],
)


interview_summary_schema = extend_schema(
    summary="📊 Get Interview Summary & Diagnosis",
    tags=["📋 Interview"],
    description="""
Get complete summary and diagnosis for a completed interview.

📋 Returns:
- Interview ID
- Diagnosis result with criteria met
- Number of completed and total questions
- Completion percentage

⚠️ Only available for completed interviews.

🔐 JWT authentication required
    """,
    responses={
        200: inline_serializer(
            name="InterviewSummaryResponse",
            fields={
                "interview_id": serializers.CharField(),
                "diagnosis_result": serializers.DictField(),
                "completed_questions": serializers.IntegerField(),
                "total_questions": serializers.IntegerField(),
                "completion_percentage": serializers.FloatField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "📊 Summary Response - Major Depression Diagnosed",
            value={
                "interview_id": "550e8400-e29b-41d4-a716-446655440001",
                "diagnosis_result": {
                    "module": "Module A - Mood Episodes",
                    "completed_at": "2026-06-21T11:45:00Z",
                    "depression": {
                        "diagnosed": True,
                        "symptoms_counted": 6,
                        "required_symptoms_count": 5,
                        "criteria_met": [
                            "A1 - Depressed mood",
                            "A2 - Loss of interest or pleasure",
                            "A4 - Insomnia or hypersomnia",
                            "A5 - Fatigue or loss of energy",
                            "A7 - Diminished ability to think or concentrate",
                            "A9 - Recurrent thoughts of death",
                        ],
                    },
                    "mania": {
                        "diagnosed": False,
                        "symptoms_counted": 1,
                        "required_symptoms_count": 4,
                        "criteria_met": ["A29 - Elevated mood"],
                    },
                    "hypomania": {
                        "diagnosed": False,
                        "symptoms_counted": 0,
                        "required_symptoms_count": 4,
                        "criteria_met": [],
                    },
                },
                "completed_questions": 53,
                "total_questions": 53,
                "completion_percentage": 100.0,
            },
            response_only=True,
        ),
        OpenApiExample(
            "📊 Summary Response - No Diagnosis",
            value={
                "interview_id": "550e8400-e29b-41d4-a716-446655440002",
                "diagnosis_result": {
                    "module": "Module A - Mood Episodes",
                    "completed_at": "2026-06-21T14:30:00Z",
                    "depression": {
                        "diagnosed": False,
                        "symptoms_counted": 2,
                        "required_symptoms_count": 5,
                        "criteria_met": ["A1 - Depressed mood", "A5 - Fatigue"],
                    },
                    "mania": {
                        "diagnosed": False,
                        "symptoms_counted": 0,
                        "required_symptoms_count": 4,
                        "criteria_met": [],
                    },
                    "hypomania": {
                        "diagnosed": False,
                        "symptoms_counted": 0,
                        "required_symptoms_count": 4,
                        "criteria_met": [],
                    },
                },
                "completed_questions": 53,
                "total_questions": 53,
                "completion_percentage": 100.0,
            },
            response_only=True,
        ),
        OpenApiExample(
            "📊 Summary Response - Bipolar I (Manic Episode)",
            value={
                "interview_id": "550e8400-e29b-41d4-a716-446655440003",
                "diagnosis_result": {
                    "module": "Module A - Mood Episodes",
                    "completed_at": "2026-06-21T16:00:00Z",
                    "depression": {
                        "diagnosed": False,
                        "symptoms_counted": 3,
                        "required_symptoms_count": 5,
                        "criteria_met": ["A1", "A5", "A7"],
                    },
                    "mania": {
                        "diagnosed": True,
                        "symptoms_counted": 5,
                        "required_symptoms_count": 4,
                        "criteria_met": [
                            "A29 - Elevated mood",
                            "A30 - Irritability",
                            "A31 - Inflated self-esteem",
                            "A32 - Decreased need for sleep",
                            "A35 - Increase in goal-directed activity",
                        ],
                    },
                    "hypomania": {
                        "diagnosed": True,
                        "symptoms_counted": 4,
                        "required_symptoms_count": 4,
                        "criteria_met": [
                            "A41 - Elevated mood for 4+ days",
                            "A42 - Irritability",
                            "A43 - Inflated self-esteem",
                            "A44 - Decreased need for sleep",
                        ],
                    },
                },
                "completed_questions": 53,
                "total_questions": 53,
                "completion_percentage": 100.0,
            },
            response_only=True,
        ),
    ],
)