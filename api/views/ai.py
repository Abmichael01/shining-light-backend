"""
AI Views

Endpoints for the AI feature catalog and individual AI features.
All endpoints require authenticated admin/staff users.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import AIFeature
from api.permissions import IsAdminOrStaff
from api.services.ai import (
    QuestionGeneratorService,
    ReportGeneratorService,
    ChatService,
    list_templates_for_page,
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
# AI Chat
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """Stateless chat completion. Frontend manages history."""
    try:
        messages = request.data.get('messages', [])
        page_type = (request.data.get('page_type') or '').strip()

        reply_text = ChatService.reply(
            messages=messages, 
            page_type=page_type,
            user=request.user
        )
        return Response({'reply': reply_text}, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response(
            {'error': f'Chat failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
