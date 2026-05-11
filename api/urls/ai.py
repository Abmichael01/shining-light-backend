from django.urls import path
from api.views.ai import (
    list_ai_features,
    generate_questions,
    save_generated_questions,
    list_report_templates,
    generate_report,
    admin_insights,
    chat,
    approve_chat_action,
    chat_action_history,
    revert_chat_action,
    message_drafts,
    message_draft_detail,
    message_draft_approve_send,
    message_draft_reject,
)

urlpatterns = [
    path('features/', list_ai_features, name='ai-features'),
    path('questions/generate/', generate_questions, name='ai-generate-questions'),
    path('questions/save/', save_generated_questions, name='ai-save-questions'),
    path('reports/templates/', list_report_templates, name='ai-report-templates'),
    path('reports/generate/', generate_report, name='ai-generate-report'),
    path('admin/insights/', admin_insights, name='ai-admin-insights'),
    path('chat/', chat, name='ai-chat'),
    path('chat/actions/history/', chat_action_history, name='ai-chat-action-history'),
    path('chat/actions/approve/', approve_chat_action, name='ai-chat-action-approve'),
    path('chat/actions/<int:action_id>/revert/', revert_chat_action, name='ai-chat-action-revert'),
    path('message-drafts/', message_drafts, name='ai-message-drafts'),
    path('message-drafts/<int:draft_id>/', message_draft_detail, name='ai-message-draft-detail'),
    path('message-drafts/<int:draft_id>/approve-send/', message_draft_approve_send, name='ai-message-draft-approve-send'),
    path('message-drafts/<int:draft_id>/reject/', message_draft_reject, name='ai-message-draft-reject'),
]
