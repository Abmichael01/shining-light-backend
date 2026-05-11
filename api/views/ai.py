"""
AI Views

Endpoints for the AI feature catalog and individual AI features.
All endpoints require authenticated admin/staff users.
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import AIActionLog, AIFeature, AIMessageDraft, Class, FeePayment, FeeType, GuardianMessage, Staff, Student
from api.pagination import StandardResultsSetPagination
from api.permissions import IsAdminOrStaff, IsSchoolAdmin
from api.serializers.communication import AIActionLogSerializer, AIMessageDraftSerializer
from api.services.ai import (
    QuestionGeneratorService,
    ReportGeneratorService,
    ChatService,
    list_templates_for_page,
)
from api.services.ai.message_drafts import (
    approve_and_send_draft,
    create_ai_message_draft,
    reject_draft,
)
from api.services.ai.skills.data_retrieval import (
    approve_fee_type_amount_update,
    approve_record_fields_update,
    create_ai_action_log,
    revert_ai_action,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_ai_features(request):
    """List active AI features for the current user's audience."""
    user_type = getattr(request.user, 'user_type', None) or 'admin'

    features = AIFeature.objects.filter(is_active=True).filter(
        # 'all' audience features are visible to everyone
        # otherwise audience must match the requesting user's type
        audience__in=[user_type, 'all']
    ).order_by('order', 'name')

    data = [
        {
            'slug': f.slug,
            'name': f.name,
            'description': f.description,
            'audience': f.audience,
            'status': f.status,
            'icon': f.icon,
            'route': f.route,
        }
        for f in features
    ]
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def generate_questions(request):
    """Generate draft questions via OpenAI. Does NOT save them."""
    try:
        subject_id = request.data.get('subject_id')
        topic_id = request.data.get('topic_id')
        count = int(request.data.get('count', 5))
        difficulty = request.data.get('difficulty', 'medium')
        question_type = request.data.get('question_type', 'multiple_choice')
        format_style = request.data.get('format_style', 'general')
        extra_context = request.data.get('extra_context') or None

        if not subject_id:
            return Response({'error': 'subject_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        questions = QuestionGeneratorService.generate(
            subject_id=str(subject_id),
            topic_id=int(topic_id) if topic_id else None,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
            format_style=format_style,
            extra_context=extra_context,
        )
        return Response({'questions': questions}, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        # OpenAI key missing or similar config error
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response(
            {'error': f'Failed to generate questions: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def save_generated_questions(request):
    """Save reviewed/edited questions to the question bank as unverified drafts."""
    try:
        questions = request.data.get('questions', [])
        marks = int(request.data.get('marks', 1))

        if not questions:
            return Response({'error': 'questions array is required'}, status=status.HTTP_400_BAD_REQUEST)

        saved = QuestionGeneratorService.save_questions(
            questions=questions,
            created_by=request.user,
            marks=marks,
        )
        return Response(
            {'saved_count': len(saved), 'question_ids': [q.id for q in saved]},
            status=status.HTTP_201_CREATED,
        )

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'error': f'Failed to save questions: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# AI Reports
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def list_report_templates(request):
    """Return registered report templates for a given page type."""
    page_type = request.query_params.get('page_type', '').strip()
    if not page_type:
        return Response({'error': 'page_type query param is required'},
                        status=status.HTTP_400_BAD_REQUEST)
    templates = list_templates_for_page(page_type)
    return Response(templates, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def generate_report(request):
    """Generate a structured AI report from a registered template."""
    try:
        slug = request.data.get('slug')
        payload = request.data.get('payload') or {}
        extra_instruction = (request.data.get('extra_instruction') or '').strip()

        if not slug:
            return Response({'error': 'slug is required'}, status=status.HTTP_400_BAD_REQUEST)

        report = ReportGeneratorService.generate(
            slug=slug,
            payload=payload,
            extra_instruction=extra_instruction,
        )
        return Response(report, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response(
            {'error': f'Failed to generate report: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# AI Admin Insights
# ---------------------------------------------------------------------------

def _counts_by(queryset, field):
    return list(queryset.values(field).annotate(count=Count('id')).order_by(field))


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_insights(request):
    """Return AI/admin analytics, behavior signals, and action notifications."""
    today = timezone.localdate()
    start_30 = today - timedelta(days=29)
    start_7 = today - timedelta(days=6)

    payment_rows = (
        FeePayment.objects.filter(payment_date__gte=start_30)
        .values('payment_date')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('payment_date')
    )
    payment_by_day = {
        row['payment_date'].isoformat(): {
            'date': row['payment_date'].isoformat(),
            'total': float(row['total'] or 0),
            'count': row['count'],
        }
        for row in payment_rows
    }
    revenue_trend = [
        payment_by_day.get(
            (start_30 + timedelta(days=offset)).isoformat(),
            {'date': (start_30 + timedelta(days=offset)).isoformat(), 'total': 0, 'count': 0},
        )
        for offset in range(30)
    ]

    drafts = AIMessageDraft.objects.all()
    actions = AIActionLog.objects.all()
    approved_actions = actions.filter(status='approved')
    recent_rejections = list(
        drafts.filter(status='rejected')
        .exclude(rejection_reason='')
        .order_by('-rejected_at')
        .values('id', 'channel', 'target_group', 'rejection_reason', 'rejected_at')[:8]
    )
    for item in recent_rejections:
        if item.get('rejected_at'):
            item['rejected_at'] = item['rejected_at'].isoformat()

    total_drafts = drafts.count()
    rejected_drafts = drafts.filter(status='rejected').count()
    sent_drafts = drafts.filter(status='sent').count()
    failed_drafts = drafts.filter(status='failed').count()
    recent_action_rows = list(
        actions.select_related('approved_by')
        .order_by('-approved_at')
        .values('id', 'action_type', 'status', 'summary', 'approved_by__email', 'approved_at')[:8]
    )
    for item in recent_action_rows:
        if item.get('approved_at'):
            item['approved_at'] = item['approved_at'].isoformat()

    notifications = []
    reversible_count = approved_actions.count()
    if reversible_count:
        notifications.append({
            'tone': 'info',
            'title': 'Reversible AI actions',
            'message': f'{reversible_count} approved AI action(s) can still be reverted if needed.',
        })
    if failed_drafts:
        notifications.append({
            'tone': 'danger',
            'title': 'Failed AI messages',
            'message': f'{failed_drafts} AI draft(s) failed during delivery and need review.',
        })
    recent_rejected_count = drafts.filter(status='rejected', rejected_at__date__gte=start_7).count()
    if recent_rejected_count:
        notifications.append({
            'tone': 'warning',
            'title': 'Recent draft feedback',
            'message': f'{recent_rejected_count} draft(s) were rejected recently. Lumina will use those reasons as feedback.',
        })

    recommendations = []
    pending_applications = Student.objects.filter(status__in=['applicant', 'under_review']).count()
    if pending_applications:
        recommendations.append(f'Review {pending_applications} pending applicant record(s).')
    if total_drafts and rejected_drafts / total_drafts >= 0.25:
        recommendations.append('Draft rejection rate is high; review rejection reasons before sending bulk messages.')
    if failed_drafts:
        recommendations.append('Check failed message delivery settings or recipient contact quality.')
    if not recommendations:
        recommendations.append('AI workflows look stable. Keep using approvals and rejection feedback to train Lumina.')

    return Response(
        {
            'overview': {
                'students_total': Student.objects.count(),
                'students_by_status': _counts_by(Student.objects.all(), 'status'),
                'pending_applications': pending_applications,
                'active_staff': Staff.objects.filter(status='active').count(),
                'classes_total': Class.objects.count(),
                'fee_types_total': FeeType.objects.count(),
                'revenue_30_days': float(
                    FeePayment.objects.filter(payment_date__gte=start_30).aggregate(total=Sum('amount'))['total'] or 0
                ),
                'payments_30_days': FeePayment.objects.filter(payment_date__gte=start_30).count(),
                'guardian_messages_30_days': GuardianMessage.objects.filter(created_at__date__gte=start_30).count(),
                'ai_actions_total': actions.count(),
                'ai_actions_reversible': reversible_count,
                'ai_drafts_total': total_drafts,
                'ai_drafts_sent': sent_drafts,
                'ai_drafts_rejected': rejected_drafts,
                'ai_drafts_failed': failed_drafts,
            },
            'trends': {
                'revenue_by_day': revenue_trend,
                'drafts_by_status': _counts_by(drafts, 'status'),
                'actions_by_type': _counts_by(actions, 'action_type'),
                'actions_by_status': _counts_by(actions, 'status'),
            },
            'learning_signals': {
                'recent_rejections': recent_rejections,
                'recent_actions': recent_action_rows,
                'draft_acceptance_rate': round((sent_drafts / total_drafts) * 100, 1) if total_drafts else 0,
                'draft_rejection_rate': round((rejected_drafts / total_drafts) * 100, 1) if total_drafts else 0,
            },
            'notifications': notifications,
            'recommendations': recommendations,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# AI Chat
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """Stateless chat completion. Frontend manages history."""
    try:
        messages = request.data.get('messages', [])
        page_type = (request.data.get('page_type') or '').strip()

        result = ChatService.reply(
            messages=messages, 
            page_type=page_type,
            user=request.user
        )
        return Response(result, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response(
            {'error': f'Chat failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def approve_chat_action(request):
    """Approve a pending action that Lumina prepared in chat."""
    action_type = request.data.get('type') or request.data.get('action_type')
    payload = request.data.get('payload') or {}

    if action_type == 'update_fee_type_amount':
        result = approve_fee_type_amount_update(payload, request.user)
    elif action_type == 'update_record_fields':
        result = approve_record_fields_update(payload, request.user)
    else:
        return Response(
            {'error': 'Unsupported chat action.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if result.get('error'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    action_log = create_ai_action_log(
        action_type=action_type,
        payload=payload,
        result=result,
        user=request.user,
        label=request.data.get('label') or '',
        summary=request.data.get('summary') or '',
    )

    return Response(
        {
            'message': result.get('note') or 'Action approved successfully.',
            'result': result,
            'action_log': AIActionLogSerializer(action_log).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def chat_action_history(request):
    """List approved/reverted AI chat actions for admin audit."""
    queryset = AIActionLog.objects.select_related('approved_by', 'reverted_by').all()
    status_filter = request.query_params.get('status')
    action_type = request.query_params.get('action_type')

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if action_type:
        queryset = queryset.filter(action_type=action_type)

    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = AIActionLogSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def revert_chat_action(request, action_id):
    """Revert an approved AI action if the target records are unchanged."""
    try:
        action_log = AIActionLog.objects.get(pk=action_id)
    except AIActionLog.DoesNotExist:
        return Response({'error': 'AI action not found.'}, status=status.HTTP_404_NOT_FOUND)

    result = revert_ai_action(action_log, request.user)
    if result.get('error'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    action_log.refresh_from_db()
    return Response(
        {
            'message': result.get('note') or 'Action reverted.',
            'result': result,
            'action_log': AIActionLogSerializer(action_log).data,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# AI Message Drafts
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def message_drafts(request):
    """List drafts or generate a new AI message draft for admin approval."""
    if request.method == 'GET':
        queryset = AIMessageDraft.objects.select_related(
            'class_model',
            'created_by',
            'approved_by',
            'sent_by',
        ).all()
        status_filter = request.query_params.get('status')
        channel_filter = request.query_params.get('channel')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if channel_filter:
            queryset = queryset.filter(channel=channel_filter)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AIMessageDraftSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = AIMessageDraftSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        draft = create_ai_message_draft(serializer.validated_data, request.user)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response(
            {'error': f'Failed to generate message draft: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(AIMessageDraftSerializer(draft).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def message_draft_detail(request, draft_id):
    """Retrieve, edit, or delete a draft before it is sent."""
    try:
        draft = AIMessageDraft.objects.select_related(
            'class_model',
            'created_by',
            'approved_by',
            'sent_by',
        ).get(pk=draft_id)
    except AIMessageDraft.DoesNotExist:
        return Response({'error': 'Draft not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(AIMessageDraftSerializer(draft).data, status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        if draft.status == 'sent':
            return Response({'error': 'Sent drafts cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)
        draft.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if draft.status == 'sent':
        return Response({'error': 'Sent drafts cannot be edited'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = AIMessageDraftSerializer(draft, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def message_draft_approve_send(request, draft_id):
    """Approve a draft and deliver it through the configured email/SMS provider."""
    try:
        draft = AIMessageDraft.objects.get(pk=draft_id)
    except AIMessageDraft.DoesNotExist:
        return Response({'error': 'Draft not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        result = approve_and_send_draft(draft, request.user)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Failed to send draft: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {
            'message': result['summary'],
            'draft': AIMessageDraftSerializer(draft).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def message_draft_reject(request, draft_id):
    """Reject a draft so it cannot be sent accidentally."""
    try:
        draft = AIMessageDraft.objects.get(pk=draft_id)
    except AIMessageDraft.DoesNotExist:
        return Response({'error': 'Draft not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        reject_draft(draft, request.user, request.data.get('reason', ''))
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(AIMessageDraftSerializer(draft).data, status=status.HTTP_200_OK)
