from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from api.services.cbt_passcode import CBTPasscodeService
from api.services.cbt_session import CBTSessionService
from api.permissions import IsAdminOrStaff
from api.models import Student

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def generate_passcode(request):
    """Generate a new CBT passcode with optional exam and exam hall assignment"""
    try:
        student_id = request.data.get('student_id')
        expires_in_hours = request.data.get('expires_in_hours', 2)
        exam_id = request.data.get('exam_id')
        exam_hall_id = request.data.get('exam_hall_id')
        if not student_id:
            return Response({'error': 'Student ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            expires_in_hours = int(expires_in_hours)
            if not 1 <= expires_in_hours <= 24: raise ValueError()
        except (ValueError, TypeError):
            return Response({'error': 'Expires in hours must be between 1 and 24'}, status=status.HTTP_400_BAD_REQUEST)
        passcode_data = CBTPasscodeService.generate_passcode(student_id=student_id, expires_in_hours=expires_in_hours, 
                                                            created_by=request.user, exam_id=exam_id, exam_hall_id=exam_hall_id)
        return Response(passcode_data, status=status.HTTP_201_CREATED)
    except ValueError as e: return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e: return Response({'error': f'Failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_passcode(request):
    """Student login with passcode"""
    try:
        admission_number = request.data.get('admission_number')
        passcode = request.data.get('passcode')
        if not all([admission_number, passcode]):
            return Response({'error': 'Admission number and passcode are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            student = Student.objects.get(admission_number=admission_number)
        except Student.DoesNotExist: return Response({'error': 'Invalid admission number'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            CBTPasscodeService.validate_passcode(passcode=passcode, student_id=str(student.id))
            used_passcode_data = CBTPasscodeService.use_passcode(passcode=passcode, ip_address=request.META.get('REMOTE_ADDR'), 
                                                                user_agent=request.META.get('HTTP_USER_AGENT', ''))
        except ValueError: return Response({'error': 'Invalid admission number or passcode'}, status=status.HTTP_400_BAD_REQUEST)
        session_data = CBTSessionService.create_session(student_id=student.admission_number, passcode=passcode, 
                                                       ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''))
        response = Response({
            'success': True, 'message': 'Login successful',
            'student': {'id': student.id, 'admission_number': student.admission_number or ''},
            'session': {'token': session_data['session_token'], 'expires_at': session_data['expires_at'], 'created_at': session_data['created_at']},
            'passcode': {k: used_passcode_data.get(k) for k in ['used_at', 'seat_number', 'exam_hall_id', 'exam_id']}
        }, status=status.HTTP_200_OK)
        cookie_kwargs = {'max_age': 7200, 'httponly': True, 'secure': getattr(settings, 'SESSION_COOKIE_SECURE', False), 
                         'samesite': getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')}
        cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
        if cookie_domain: cookie_kwargs['domain'] = cookie_domain
        response.set_cookie('cbt_session_token', session_data['session_token'], **cookie_kwargs)
        return response
    except Exception as e: return Response({'error': f'Login failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def revoke_passcode(request):
    try:
        passcode = request.data.get('passcode')
        if not passcode: return Response({'error': 'Passcode is required'}, status=status.HTTP_400_BAD_REQUEST)
        if CBTPasscodeService.revoke_passcode(passcode): return Response({'success': True})
        return Response({'error': 'Passcode not found or expired'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_active_passcode(request):
    student_id = request.query_params.get('student_id')
    if not student_id: return Response({'error': 'ID required'}, status=status.HTTP_400_BAD_REQUEST)
    data = CBTPasscodeService.get_active_passcode(student_id)
    if data: return Response(data)
    return Response({'error': 'No active passcode found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_passcode_stats(request):
    return Response(CBTPasscodeService.get_passcode_stats())

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_all_passcodes(request):
    include_expired = request.query_params.get('include_expired', 'true').lower() == 'true'
    return Response(CBTPasscodeService.get_all_passcodes(include_expired=include_expired))

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def delete_all_passcodes(request):
    deleted = CBTPasscodeService.delete_all_passcodes()
    return Response({'success': True, 'deleted_count': deleted}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_all_active_passcodes(request):
    """Get all active (non-expired) passcodes"""
    return Response(CBTPasscodeService.get_all_passcodes(include_expired=False))
