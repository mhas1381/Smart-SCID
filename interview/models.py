from django.db import models
from django.conf import settings
from accounts.models import Patient
import uuid


class Interview(models.Model):
    """
    Represents a complete interview session with a patient
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='interviews')
    clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conducted_interviews')
    module = models.ForeignKey('InterviewModule', on_delete=models.CASCADE, related_name='interviews')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_question = models.ForeignKey('Question', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_in_interviews')
    
    # ===== Timestamps =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Interview {self.id} - {self.patient.get_full_name()} - {self.module.name}"


class InterviewModule(models.Model):
    """
    Represents a SCID-5 module (e.g., Module A for mood episodes)
    """
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    # ===== Timestamps =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.name} - {self.version}"


class Question(models.Model):
    """
    Represents a single question in the interview
    """
    
    QUESTION_TYPES = [
        ('boolean', 'Yes/No'),
        ('multiple_choice', 'Multiple Choice'),
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('rating', 'Rating Scale'),
    ]
    
    id = models.CharField(max_length=50, primary_key=True)
    module = models.ForeignKey(InterviewModule, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='boolean')
    is_criteria = models.BooleanField(default=False)
    criteria_number = models.CharField(max_length=10, blank=True)
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    has_jump_logic = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.id} - {self.text[:50]}..."


class JumpRule(models.Model):
    """
    Defines conditional jump logic for questions
    """
    
    CONDITION_TYPES = [
        ('boolean', 'Boolean'),
        ('multiple_choice', 'Multiple Choice'),
        ('text', 'Text Match'),
        ('range', 'Number Range'),
    ]
    
    from_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='jump_rules')
    to_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='jumps_to', null=True, blank=True)
    condition = models.CharField(max_length=100)
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPES)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['from_question', 'condition']
    
    def __str__(self):
        target = self.to_question.id if self.to_question else "END"
        return f"Jump from {self.from_question.id} to {target} if {self.condition}"


class Answer(models.Model):
    """
    Represents a patient's answer to a question
    """
    
    ANSWER_TYPES = [
        ('boolean', 'Boolean'),
        ('multiple_choice', 'Multiple Choice'),
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('rating', 'Rating'),
    ]
    
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_type = models.CharField(max_length=20, choices=ANSWER_TYPES)
    value = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['interview', 'question']
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Answer for {self.question.id} in {self.interview.id}"
    
    @property
    def boolean_value(self):
        if isinstance(self.value, dict):
            return self.value.get('boolean', False)
        return bool(self.value)

    @property
    def text_value(self):
        if isinstance(self.value, dict):
            return self.value.get('text', '')
        return str(self.value) if self.value is not None else ''

    @property
    def number_value(self):
        if isinstance(self.value, dict):
            return self.value.get('number', 0)
        try:
            return float(self.value)
        except (TypeError, ValueError):
            return 0