from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.models.academic import SystemSetting
from api.models.ai.student_tutor import StudentAITutorChat, StudentAITutorMessage
from api.services.ai.tutor_service import TutorService
from api.serializers.student import StudentSerializer
import json


def _student_ai_block_response(request):
    """Return a 403 Response if student AI is disabled by admin, else None.

    Admins/staff are never affected — the `is_ai_enabled` flag is labeled
    'enable student AI' on the model and only restricts the student portal.
    """
    if not hasattr(request.user, 'student_profile'):
        return None
    settings_obj = SystemSetting.load()
    if settings_obj.is_ai_enabled:
        return None
    return Response(
        {
            'error': settings_obj.ai_disabled_message
                     or 'AI features are temporarily unavailable for students.',
            'ai_disabled': True,
        },
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_tutor_session(request):
    """Start a new AI Tutor session for a student."""
    try:
        # Ensure user is a student
        if not hasattr(request.user, 'student_profile'):
            return Response({'error': 'Only students can access the AI Tutor.'}, status=status.HTTP_403_FORBIDDEN)

        blocked = _student_ai_block_response(request)
        if blocked is not None:
            return blocked

        student = request.user.student_profile
        subject_id = request.data.get('subject_id')
        topic_id = request.data.get('topic_id')
        title = request.data.get('title', '')

        chat = TutorService.get_or_create_chat(
            student=student,
            subject_id=subject_id,
            topic_id=topic_id,
            title=title
        )

        student_info = {
            'class_name': student.class_model.name if student.class_model else '',
            'class_code': student.class_model.class_code if student.class_model else '',
        }

        return Response({
            'chat_id': chat.id,
            'title': chat.title,
            'subject_id': chat.subject_id,
            'subject_name': chat.subject.name if chat.subject else '',
            'topic_id': chat.topic_id,
            'topic_name': chat.topic.name if chat.topic else '',
            'student': student_info,
            'created_at': chat.created_at
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tutor_sessions(request):
    """List previous AI Tutor sessions for the student."""
    if not hasattr(request.user, 'student_profile'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    blocked = _student_ai_block_response(request)
    if blocked is not None:
        return blocked

    chats = request.user.student_profile.ai_tutor_chats.select_related('subject', 'topic').all()
    data = [
        {
            'id': c.id,
            'title': c.title,
            'subject_id': c.subject_id,
            'subject_name': c.subject.name if c.subject else '',
            'topic_id': c.topic_id,
            'topic_name': c.topic.name if c.topic else '',
            'created_at': c.created_at,
            'updated_at': c.updated_at
        }
        for c in chats
    ]
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def tutor_chat_detail(request, chat_id):
    """Get history or send a message to a specific tutor session."""
    blocked = _student_ai_block_response(request)
    if blocked is not None:
        return blocked

    try:
        chat = StudentAITutorChat.objects.get(pk=chat_id, student=request.user.student_profile)
    except StudentAITutorChat.DoesNotExist:
        return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        messages = chat.messages.all().order_by('created_at')
        history = []
        for m in messages:
            content = m.content
            if m.role == 'assistant':
                try:
                    content = json.loads(m.content)
                except:
                    pass
            history.append({
                'id': m.id,
                'role': m.role,
                'content': content,
                'created_at': m.created_at
            })
        return Response({
            'chat_id': chat.id,
            'title': chat.title,
            'subject_id': chat.subject_id,
            'subject_name': chat.subject.name if chat.subject else '',
            'topic_id': chat.topic_id,
            'topic_name': chat.topic.name if chat.topic else '',
            'history': history
        }, status=status.HTTP_200_OK)

    # POST - Send message and get reply
    user_message = request.data.get('message', '').strip()
    if not user_message:
        return Response({'error': 'Message is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        reply_data = TutorService.reply(chat, user_message)
        return Response(reply_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Tutor failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
