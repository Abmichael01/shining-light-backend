from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from api.services.cbt_session import CBTSessionService
from api.permissions import IsAdminOrStaff
from api.authentication import CBTSessionAuthentication
from api.models import Student
from api.serializers.student import CBTStudentProfileSerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def validate_cbt_session(request):
    try:
        session_token = request.META.get('HTTP_X_CBT_SESSION') or request.COOKIES.get('cbt_session_token')
        if not session_token: return Response({'error': 'Token required'}, status=status.HTTP_401_UNAUTHORIZED)
        session_data = CBTSessionService.validate_session(session_token)
        return Response({'valid': True, 'session': session_data}, status=status.HTTP_200_OK)
    except ValueError as e: return Response({'valid': False, 'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_cbt_session(request):
    try:
        session_token = request.META.get('HTTP_X_CBT_SESSION') or request.COOKIES.get('cbt_session_token')
        if not session_token: return Response({'error': 'Token required'}, status=status.HTTP_401_UNAUTHORIZED)
        session_data = CBTSessionService.refresh_session(session_token)
        response = Response({'success': True, 'session': session_data}, status=status.HTTP_200_OK)
        cookie_kwargs = {'max_age': 7200, 'httponly': True, 'secure': getattr(settings, 'SESSION_COOKIE_SECURE', False), 
                         'samesite': getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')}
        cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
        if cookie_domain: cookie_kwargs['domain'] = cookie_domain
        response.set_cookie('cbt_session_token', session_data['session_token'], **cookie_kwargs)
        return response
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def logout_cbt_session(request):
    try:
        session_token = request.META.get('HTTP_X_CBT_SESSION') or request.COOKIES.get('cbt_session_token')
        if not session_token: return Response({'error': 'Token required'}, status=status.HTTP_401_UNAUTHORIZED)
        success = CBTSessionService.terminate_session(session_token)
        response = Response({'success': success, 'message': 'Logged out'}, status=status.HTTP_200_OK)
        response.delete_cookie('cbt_session_token', domain=getattr(settings, 'SESSION_COOKIE_DOMAIN', None), 
                               samesite=getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax'))
        return response
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_cbt_session_stats(request):
    return Response(CBTSessionService.get_session_stats(), status=status.HTTP_200_OK)

@api_view(['GET'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def get_cbt_student_profile(request):
    try:
        student = Student.objects.select_related('school', 'class_model').prefetch_related(
            'subject_registrations__subject', 'subject_registrations__session_term'
        ).get(admission_number=request.user.admission_number)
        return Response(CBTStudentProfileSerializer(student).data, status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
