from django.urls import path
from api.views.ai import (
    list_ai_features,
    generate_questions,
    save_generated_questions,
    list_report_templates,
    generate_report,
    chat,
)

urlpatterns = [
    path('features/', list_ai_features, name='ai-features'),
    path('questions/generate/', generate_questions, name='ai-generate-questions'),
    path('questions/save/', save_generated_questions, name='ai-save-questions'),
    path('reports/templates/', list_report_templates, name='ai-report-templates'),
    path('reports/generate/', generate_report, name='ai-generate-report'),
    path('chat/', chat, name='ai-chat'),
]
