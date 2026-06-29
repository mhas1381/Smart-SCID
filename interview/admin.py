from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import (
    Interview,
    InterviewModule,
    Question,
    JumpRule,
    Answer
)


# ============================================================
# INLINES
# ============================================================

class QuestionInline(admin.TabularInline):
    """
    Inline for questions within module admin.
    """
    model = Question
    extra = 0
    fields = ('id', 'text', 'question_type', 'is_criteria', 'criteria_number', 'order', 'has_jump_logic')
    readonly_fields = ('id', 'text')
    ordering = ('order',)
    can_delete = True
    show_change_link = True


class JumpRuleInline(admin.TabularInline):
    """
    Inline for jump rules within question admin.
    """
    model = JumpRule
    fk_name = 'from_question'
    extra = 1
    fields = ('to_question', 'condition', 'condition_type')
    ordering = ('from_question',)


class AnswerInline(admin.TabularInline):
    """
    Inline for answers within interview admin.
    """
    model = Answer
    extra = 1
    fields = ('question', 'answer_type', 'value', 'notes')
    ordering = ('question__order',)
    can_delete = True
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'value':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 2, 'cols': 40})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# ============================================================
# INTERVIEW MODULE ADMIN
# ============================================================

@admin.register(InterviewModule)
class InterviewModuleAdmin(admin.ModelAdmin):
    """
    Admin for Interview Module with questions inline.
    """
    inlines = [QuestionInline]

    list_display = (
        'name',
        'version',
        'is_active',
        'order',
        'question_count',
        'interview_count',
    )

    list_filter = (
        'is_active',
        'version',
    )

    search_fields = (
        'name',
        'description',
    )

    ordering = ('order',)
    list_per_page = 20
    save_on_top = True

    fieldsets = (
        (_('Module Information'), {
            'fields': (
                'name',
                'description',
                'version',
                'is_active',
                'order',
            )
        }),
    )

    def question_count(self, obj):
        """Display number of questions in module."""
        count = obj.questions.count()
        if count > 0:
            url = reverse('admin:interview_question_changelist') + f'?module__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    question_count.short_description = _('Questions')
    question_count.admin_order_field = 'questions__count'

    def interview_count(self, obj):
        """Display number of interviews using this module."""
        count = obj.interviews.count()
        if count > 0:
            url = reverse('admin:interview_interview_changelist') + f'?module__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    interview_count.short_description = _('Interviews')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('questions', 'interviews')


# ============================================================
# QUESTION ADMIN
# ============================================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """
    Admin for Questions with jump rules inline.
    """
    inlines = [JumpRuleInline]

    list_display = (
        'id',
        'text_preview',
        'module_link',
        'question_type',
        'is_criteria',
        'criteria_number',
        'order',
        'has_jump_logic',
    )

    list_filter = (
        'module',
        'question_type',
        'is_criteria',
        'is_required',
        'has_jump_logic',
    )

    search_fields = (
        'id',
        'text',
        'criteria_number',
    )

    ordering = ('module__order', 'order')
    list_per_page = 50
    save_on_top = True

    fieldsets = (
        (_('Question Information'), {
            'fields': (
                'id',
                'module',
                'text',
                'question_type',
                'order',
            )
        }),
        (_('Criteria Information'), {
            'fields': (
                'is_criteria',
                'criteria_number',
                'is_required',
                'has_jump_logic',
            )
        }),
    )

    readonly_fields = ('id',)

    def text_preview(self, obj):
        """Show truncated question text."""
        if len(obj.text) > 80:
            return f"{obj.text[:80]}..."
        return obj.text
    text_preview.short_description = _('Question')

    def module_link(self, obj):
        """Link to module admin."""
        if obj.module:
            url = reverse('admin:interview_interviewmodule_change', args=[obj.module.id])
            return format_html('<a href="{}">{}</a>', url, obj.module.name)
        return '-'
    module_link.short_description = _('Module')
    module_link.admin_order_field = 'module__name'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('module')


# ============================================================
# JUMP RULE ADMIN
# ============================================================

@admin.register(JumpRule)
class JumpRuleAdmin(admin.ModelAdmin):
    """
    Admin for Jump Rules.
    """
    list_display = (
        'from_question_link',
        'to_question_link',
        'condition_preview',
        'condition_type',
        'metadata_preview',
    )

    list_filter = (
        'condition_type',
        'from_question__module',
    )

    search_fields = (
        'from_question__id',
        'to_question__id',
        'condition',
    )

    ordering = ('from_question__module__order', 'from_question__order')
    list_per_page = 50
    save_on_top = True

    fieldsets = (
        (_('Jump Rule Information'), {
            'fields': (
                'from_question',
                'to_question',
                'condition',
                'condition_type',
                'metadata',
            )
        }),
    )

    def from_question_link(self, obj):
        """Link to from_question admin."""
        if obj.from_question:
            url = reverse('admin:interview_question_change', args=[obj.from_question.id])
            return format_html('<a href="{}">{}</a>', url, obj.from_question.id)
        return '-'
    from_question_link.short_description = _('From Question')
    from_question_link.admin_order_field = 'from_question__id'

    def to_question_link(self, obj):
        """Link to to_question admin."""
        if obj.to_question:
            url = reverse('admin:interview_question_change', args=[obj.to_question.id])
            return format_html('<a href="{}">{}</a>', url, obj.to_question.id)
        return '<span style="color: #999;">END</span>'
    to_question_link.short_description = _('To Question')
    to_question_link.admin_order_field = 'to_question__id'

    def condition_preview(self, obj):
        """Show truncated condition."""
        if len(obj.condition) > 40:
            return f"{obj.condition[:40]}..."
        return obj.condition
    condition_preview.short_description = _('Condition')

    def metadata_preview(self, obj):
        """Show truncated metadata."""
        import json
        if obj.metadata:
            try:
                meta_str = json.dumps(obj.metadata, ensure_ascii=False)
                if len(meta_str) > 30:
                    return f"{meta_str[:30]}..."
                return meta_str
            except:
                return str(obj.metadata)[:30]
        return '-'
    metadata_preview.short_description = _('Metadata')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('from_question', 'to_question')


# ============================================================
# ANSWER ADMIN
# ============================================================

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """
    Admin for Answers.
    """
    list_display = (
        'id',
        'interview_link',
        'question_link',
        'answer_type',
        'value_preview',
        'timestamp_display',
        'has_notes',
    )

    list_filter = (
        'answer_type',
        'timestamp',
        'interview__status',
    )

    search_fields = (
        'interview__id',
        'question__id',
        'question__text',
        'notes',
    )

    ordering = ('-timestamp',)
    list_per_page = 50
    date_hierarchy = 'timestamp'

    raw_id_fields = ('interview', 'question')
    autocomplete_fields = ('interview', 'question')

    
    readonly_fields = ('id', 'timestamp')

    fieldsets = (
        (_('Answer Information'), {
            'fields': (
                'interview',  
                'question',  
                'answer_type',
                'value',
                'notes',
            )
        }),
        (_('Metadata'), {
            'fields': ('id', 'timestamp'),
            'classes': ('collapse',),
        }),
    )

    def interview_link(self, obj):
        """Link to interview admin."""
        if obj.interview:
            url = reverse('admin:interview_interview_change', args=[obj.interview.id])
            patient_name = obj.interview.patient.get_full_name()
            return format_html(
                '<a href="{}">{} - {}</a>',
                url,
                str(obj.interview.id)[:8],
                patient_name
            )
        return '-'
    interview_link.short_description = _('Interview')
    interview_link.admin_order_field = 'interview__id'

    def question_link(self, obj):
        """Link to question admin."""
        if obj.question:
            url = reverse('admin:interview_question_change', args=[obj.question.id])
            return format_html('<a href="{}">{}</a>', url, obj.question.id)
        return '-'
    question_link.short_description = _('Question')
    question_link.admin_order_field = 'question__id'

    def value_preview(self, obj):
        """Show answer value."""
        if isinstance(obj.value, dict):
            if 'boolean' in obj.value:
                return '✅ Yes' if obj.value['boolean'] else '❌ No'
            elif 'text' in obj.value:
                val = obj.value['text']
                if len(val) > 40:
                    return f"{val[:40]}..."
                return val
            elif 'number' in obj.value:
                return str(obj.value['number'])
            return str(obj.value)
        return str(obj.value) if obj.value is not None else '-'
    value_preview.short_description = _('Answer')

    def timestamp_display(self, obj):
        """Display formatted timestamp."""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    timestamp_display.short_description = _('Time')
    timestamp_display.admin_order_field = 'timestamp'

    def has_notes(self, obj):
        """Display if answer has notes."""
        if obj.notes:
            return format_html('<span style="color: #0a0;">📝</span>')
        return '-'
    has_notes.short_description = _('Notes')
    has_notes.boolean = False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('interview', 'question', 'interview__patient')


# ============================================================
# INTERVIEW ADMIN
# ============================================================

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    """
    Admin for Interviews with answers inline.
    """
    inlines = [AnswerInline]

    list_display = (
        'id_display',
        'patient_link',
        'clinician_link',
        'module_link',
        'status_badge',
        'progress_display',
        'current_question_link',
        'answer_count',
        'duration_display',
        'started_at_display',
    )

    list_filter = (
        'status',
        'module',
        'started_at',
    )

    search_fields = (
        'id',
        'patient__first_name',
        'patient__last_name',
        'clinician__first_name',
        'clinician__last_name',
    )

    ordering = ('-started_at',)
    list_per_page = 25
    date_hierarchy = 'started_at'
    save_on_top = True
    actions = ('mark_completed', 'mark_paused')

    readonly_fields = ('id', 'started_at', 'completed_at', 'created_at', 'updated_at')

    fieldsets = (
        (_('Interview Information'), {
            'fields': (
                'id',
                'patient',
                'clinician',
                'module',
                'status',
                'current_question',
            )
        }),
        (_('Timeline'), {
            'fields': (
                'started_at',
                'completed_at',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def id_display(self, obj):
        """Display short ID."""
        return str(obj.id)[:8]
    id_display.short_description = _('ID')
    id_display.admin_order_field = 'id'

    def patient_link(self, obj):
        """Link to patient admin (if available)."""
        if obj.patient:
            try:
                url = reverse('admin:accounts_patient_change', args=[obj.patient.id])
                return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name())
            except:
                return obj.patient.get_full_name()
        return '-'
    patient_link.short_description = _('Patient')
    patient_link.admin_order_field = 'patient__first_name'

    def clinician_link(self, obj):
        """Link to clinician user admin."""
        if obj.clinician:
            url = reverse('admin:accounts_user_change', args=[obj.clinician.id])
            return format_html('<a href="{}">{}</a>', url, obj.clinician.get_full_name())
        return '-'
    clinician_link.short_description = _('Clinician')
    clinician_link.admin_order_field = 'clinician__first_name'

    def module_link(self, obj):
        """Link to module admin."""
        if obj.module:
            url = reverse('admin:interview_interviewmodule_change', args=[obj.module.id])
            return format_html('<a href="{}">{}</a>', url, obj.module.name)
        return '-'
    module_link.short_description = _('Module')
    module_link.admin_order_field = 'module__name'

    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'pending': '#FFA500',
            'in_progress': '#007BFF',
            'completed': '#28A745',
            'paused': '#FFC107',
        }
        color = colors.get(obj.status, '#6C757D')
        status_labels = {
            'pending': '⏳ Pending',
            'in_progress': '🔄 In Progress',
            'completed': '✅ Completed',
            'paused': '⏸️ Paused',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            status_labels.get(obj.status, obj.status)
        )
    status_badge.short_description = _('Status')

    def current_question_link(self, obj):
        """Link to current question admin."""
        if obj.current_question:
            url = reverse('admin:interview_question_change', args=[obj.current_question.id])
            return format_html('<a href="{}">{}</a>', url, obj.current_question.id)
        return '-'
    current_question_link.short_description = _('Current Question')
    current_question_link.admin_order_field = 'current_question__id'

    def answer_count(self, obj):
        """Display number of answers."""
        count = obj.answers.count()
        if count > 0:
            url = reverse('admin:interview_answer_changelist') + f'?interview__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    answer_count.short_description = _('Answers')
    answer_count.admin_order_field = 'answers__count'

    def duration_display(self, obj):
        """Display interview duration."""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        elif obj.started_at:
            from django.utils import timezone
            duration = timezone.now() - obj.started_at
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if minutes > 0:
                return f"{minutes}m {seconds}s (ongoing)"
            return f"{seconds}s (ongoing)"
        return '-'
    duration_display.short_description = _('Duration')

    def started_at_display(self, obj):
        """Display formatted start time."""
        return obj.started_at.strftime('%Y-%m-%d %H:%M')
    started_at_display.short_description = _('Started')
    started_at_display.admin_order_field = 'started_at'

    def progress_display(self, obj):
        """Display interview progress as a bar."""
        total = obj.module.questions.count() if obj.module else 0
        answered = obj.answers.count()
        if total == 0:
            return '-'
        pct = int((answered / total) * 100)
        color = '#28a745' if pct >= 100 else '#007bff' if pct >= 50 else '#ffc107'
        return format_html(
            '<div style="width:80px; background:#e9ecef; border-radius:4px; overflow:hidden;">'
            '<div style="width:{}%; background:{}; height:14px;"></div></div>'
            '<small>{}/{} ({}%)</small>',
            pct, color, answered, total, pct
        )
    progress_display.short_description = _('Progress')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'patient', 'clinician', 'module', 'current_question'
        ).prefetch_related('answers')

    def save_model(self, request, obj, form, change):
        """Save model with auto-set clinician."""
        if not change and not obj.clinician:
            obj.clinician = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_('Mark selected interviews as completed'))
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(status__in=['in_progress', 'paused', 'pending']).update(
            status='completed',
            completed_at=timezone.now(),
        )
        self.message_user(request, f'{count} interview(s) marked as completed.')

    @admin.action(description=_('Mark selected interviews as paused'))
    def mark_paused(self, request, queryset):
        count = queryset.filter(status='in_progress').update(status='paused')
        self.message_user(request, f'{count} interview(s) paused.')