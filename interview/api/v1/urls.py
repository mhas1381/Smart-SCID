from django.urls import path
from .views import (
    ModuleListView,
    ModuleDetailView,
    QuestionListView,
    QuestionDetailView,
    InterviewListView,
    InterviewDetailView,
    InterviewStartView,
    InterviewProgressView,
    InterviewPauseView,
    InterviewResumeView,
    InterviewSummaryView,
)

app_name = 'interviews'

urlpatterns = [
    # Modules
    path('modules/', ModuleListView.as_view(), name='module-list'),
    path('modules/<int:id>/', ModuleDetailView.as_view(), name='module-detail'),

    # Questions
    path('questions/', QuestionListView.as_view(), name='question-list'),
    path('questions/<str:id>/', QuestionDetailView.as_view(), name='question-detail'),

    # Interviews
    path('interviews/', InterviewListView.as_view(), name='interview-list'),
    path('interviews/<uuid:id>/', InterviewDetailView.as_view(), name='interview-detail'),
    path('interviews/start/', InterviewStartView.as_view(), name='interview-start'),
    path('interviews/<uuid:id>/progress/', InterviewProgressView.as_view(), name='interview-progress'),
    path('interviews/<uuid:id>/pause/', InterviewPauseView.as_view(), name='interview-pause'),
    path('interviews/<uuid:id>/resume/', InterviewResumeView.as_view(), name='interview-resume'),
    path('interviews/<uuid:id>/summary/', InterviewSummaryView.as_view(), name='interview-summary'),
]