from rest_framework import serializers
from ...models import Interview, InterviewModule, Question, Answer, JumpRule
from accounts.models import Patient, User
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.serializers import UserSerializer


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for listing questions with basic information"""
    
    module_name = serializers.CharField(source='module.name', read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id', 'text', 'question_type', 'is_criteria', 'criteria_number', 
            'order', 'is_required', 'has_jump_logic', 'module_name'
        ]


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed question information"""
    
    module = serializers.SerializerMethodField()
    module_name = serializers.CharField(source='module.name', read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id', 'text', 'question_type', 'is_criteria', 'criteria_number', 
            'order', 'is_required', 'has_jump_logic', 'module', 'module_name'
        ]
        read_only_fields = ['id']

    def get_module(self, obj):
        """Return module name as string for compatibility"""
        return obj.module.name if obj.module else None


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new questions"""
    
    class Meta:
        model = Question
        fields = [
            'id', 'module', 'text', 'question_type', 'is_criteria', 
            'criteria_number', 'order', 'is_required', 'has_jump_logic'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Validate question data"""
        if data.get('is_criteria') and not data.get('criteria_number'):
            raise ValidationError("Criteria questions must have a criteria number")
        
        if data.get('has_jump_logic') and not data.get('module'):
            raise ValidationError("Questions with jump logic must belong to a module")
            
        return data


class InterviewModuleListSerializer(serializers.ModelSerializer):
    """Serializer for listing interview modules"""
    
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    
    class Meta:
        model = InterviewModule
        fields = [
            'id', 'name', 'description', 'version', 'is_active', 'order', 'question_count'
        ]


class InterviewModuleDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed interview module information"""
    
    questions = QuestionListSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    
    class Meta:
        model = InterviewModule
        fields = [
            'id', 'name', 'description', 'version', 'is_active', 'order', 
            'questions', 'question_count'
        ]
        read_only_fields = ['id']


class InterviewModuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new interview modules"""
    
    class Meta:
        model = InterviewModule
        fields = [
            'name', 'description', 'version', 'is_active', 'order'
        ]

    def validate_name(self, value):
        """Validate module name is not empty"""
        if not value or not value.strip():
            raise ValidationError("Module name cannot be empty")
        return value.strip()


class InterviewListSerializer(serializers.ModelSerializer):
    """Serializer for listing interviews"""
    
    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()
    module_name = serializers.CharField(source='module.name', read_only=True)
    current_question_text = serializers.CharField(source='current_question.text', read_only=True)
    answer_count = serializers.IntegerField(source='answers.count', read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'id', 'patient', 'patient_name', 'clinician', 'clinician_name',
            'module', 'module_name', 'status', 'started_at', 'completed_at',
            'current_question_text', 'answer_count'
        ]
        read_only_fields = ['id', 'patient', 'clinician', 'started_at', 'completed_at']

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()


class InterviewDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed interview information"""
    
    patient = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    clinician = UserSerializer(read_only=True)
    clinician_name = serializers.SerializerMethodField()
    module = InterviewModuleDetailSerializer(read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    current_question = QuestionDetailSerializer(read_only=True)
    answers = serializers.SerializerMethodField()
    answer_count = serializers.IntegerField(source='answers.count', read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'id', 'patient', 'patient_name', 'clinician', 'clinician_name',
            'module', 'module_name', 'status', 'started_at', 'completed_at',
            'current_question', 'answers', 'answer_count'
        ]
        read_only_fields = ['id', 'patient', 'clinician', 'started_at', 'completed_at']

    def get_patient(self, obj):
        """Return patient information"""
        from accounts.serializers import PatientListSerializer
        return PatientListSerializer(obj.patient).data

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()

    def get_answers(self, obj):
        """Return answers for this interview"""
        # Import here to avoid circular import
        from .serializers import AnswerListSerializer
        return AnswerListSerializer(obj.answers.all(), many=True).data


class InterviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new interviews"""
    
    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()
    module_name = serializers.CharField(source='module.name', read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'patient', 'patient_name', 'clinician', 'clinician_name',
            'module', 'module_name', 'status'
        ]
        read_only_fields = ['id', 'patient', 'clinician', 'status', 'started_at']

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()

    def create(self, validated_data):
        """Set clinician from context and set default status"""
        validated_data['clinician'] = self.context['request'].user
        validated_data['status'] = 'pending'
        return super().create(validated_data)


class InterviewStartSerializer(serializers.Serializer):
    """
    Serializer for starting a new interview.
    patient_id can be either UUID or integer (AutoField).
    """
    patient_id = serializers.CharField()  # Accept both UUID and integer
    module_id = serializers.IntegerField()

    def validate_patient_id(self, value):
        """
        Validate that patient exists.
        Accepts both UUID string and integer ID.
        """
        try:
            # Try to find by integer ID
            patient = Patient.objects.get(id=value)
            return patient.id  # Return the actual ID value
        except (Patient.DoesNotExist, ValueError, TypeError):
            raise ValidationError("Patient not found")

    def validate_module_id(self, value):
        try:
            module = InterviewModule.objects.get(id=value)
            if not module.is_active:
                raise ValidationError("Module is not active")
            return value
        except InterviewModule.DoesNotExist:
            raise ValidationError("Module not found")


class InterviewProgressSerializer(serializers.Serializer):
    """Serializer for progressing through interview questions"""
    
    question_id = serializers.CharField()
    answer_value = serializers.JSONField()
    answer_type = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_question_id(self, value):
        if not Question.objects.filter(id=value).exists():
            raise ValidationError("Question not found")
        return value

    def validate_answer_type(self, value):
        valid_types = ['boolean', 'multiple_choice', 'text', 'number', 'date', 'rating']
        if value not in valid_types:
            raise ValidationError(
                f"Invalid answer type. Must be one of: {valid_types}"
            )
        return value

    def validate_answer_value(self, value):
        """Validate answer value based on answer type"""
        answer_type = self.initial_data.get('answer_type')
        
        if answer_type == 'boolean' and not isinstance(value, bool):
            raise ValidationError("Boolean answer must be true or false")
        
        if answer_type == 'number' and not isinstance(value, (int, float)):
            raise ValidationError("Number answer must be a numeric value")
        
        if answer_type == 'date':
            try:
                if isinstance(value, str):
                    # Try to parse date string
                    from datetime import datetime
                    datetime.strptime(value, '%Y-%m-%d')
                elif not isinstance(value, type(timezone.now().date())):
                    raise ValidationError("Date must be in YYYY-MM-DD format")
            except ValueError:
                raise ValidationError("Date must be in YYYY-MM-DD format")
        
        return value


class InterviewSummarySerializer(serializers.Serializer):
    """Serializer for interview summary and results"""
    
    interview_id = serializers.CharField(read_only=True)
    diagnosis_result = serializers.DictField(read_only=True)
    completed_questions = serializers.IntegerField(read_only=True)
    total_questions = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
    patient_name = serializers.SerializerMethodField()
    clinician_name = serializers.SerializerMethodField()
    module_name = serializers.CharField(read_only=True)
    duration = serializers.SerializerMethodField()

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()

    def get_duration(self, obj):
        """Calculate interview duration"""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            return duration.total_seconds() / 60  # Return in minutes
        return None


class AnswerListSerializer(serializers.ModelSerializer):
    """Serializer for listing answers"""
    
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    
    class Meta:
        model = Answer
        fields = [
            'id', 'question', 'question_text', 'question_type', 
            'answer_type', 'value', 'timestamp', 'notes'
        ]
        read_only_fields = ['id', 'timestamp']


class AnswerDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed answer information"""
    
    question = QuestionDetailSerializer(read_only=True)
    interview = InterviewListSerializer(read_only=True)
    
    class Meta:
        model = Answer
        fields = [
            'id', 'interview', 'question', 'answer_type', 'value', 
            'timestamp', 'notes'
        ]
        read_only_fields = ['id', 'timestamp']


class AnswerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new answers"""
    
    class Meta:
        model = Answer
        fields = [
            'interview', 'question', 'answer_type', 'value', 'notes'
        ]
        read_only_fields = ['id', 'timestamp']

    def validate(self, data):
        """Validate answer data"""
        # Check if answer already exists for this interview and question
        if Answer.objects.filter(
            interview=data['interview'], 
            question=data['question']
        ).exists():
            raise ValidationError("Answer for this question already exists in this interview")
        
        # Validate answer type matches question type
        if data['question'].question_type != data['answer_type']:
            raise ValidationError("Answer type must match question type")
        
        return data


class JumpRuleListSerializer(serializers.ModelSerializer):
    """Serializer for listing jump rules"""
    
    from_question_text = serializers.CharField(source='from_question.text', read_only=True)
    to_question_text = serializers.CharField(source='to_question.text', read_only=True)
    
    class Meta:
        model = JumpRule
        fields = [
            'id', 'from_question', 'from_question_text', 'to_question', 
            'to_question_text', 'condition', 'condition_type', 'metadata'
        ]


class JumpRuleDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed jump rule information"""
    
    from_question = QuestionDetailSerializer(read_only=True)
    to_question = QuestionDetailSerializer(read_only=True)
    
    class Meta:
        model = JumpRule
        fields = [
            'id', 'from_question', 'to_question', 'condition', 
            'condition_type', 'metadata'
        ]
        read_only_fields = ['id']


class JumpRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new jump rules"""
    
    class Meta:
        model = JumpRule
        fields = [
            'from_question', 'to_question', 'condition', 'condition_type', 'metadata'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Validate jump rule data"""
        if data['from_question'].module != data.get('to_question', {}).module:
            raise ValidationError("Both questions must belong to the same module")
        
        # Validate condition type matches question type
        question = data['from_question']
        condition_type = data['condition_type']
        
        if question.question_type == 'boolean' and condition_type != 'boolean':
            raise ValidationError("Boolean questions can only have boolean conditions")
        
        if question.question_type == 'multiple_choice' and condition_type != 'multiple_choice':
            raise ValidationError("Multiple choice questions can only have multiple choice conditions")
        
        return data