from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.models import ResultPin, Student, Session, SessionTerm
from api.permissions import IsAdminOrStaffOrStudent
from django.utils import timezone

class ResultPinViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ResultPin model
    """
    queryset = ResultPin.objects.all()
    permission_classes = [IsAdminOrStaffOrStudent]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'user_type', None) == 'student' and hasattr(user, 'student_profile'):
            return self.queryset.filter(student=user.student_profile)
        return self.queryset

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrStaffOrStudent])
    def validate(self, request):
        """
        Validate a PIN and mark it as used.
        Required data: pin, student_id, session_id, term_id
        """
        pin_string = request.data.get('pin')
        student_id = request.data.get('student_id')
        session_id = request.data.get('session_id')
        term_id = request.data.get('term_id')

        if not all([pin_string, student_id, session_id, term_id]):
            return Response({'error': 'All fields (pin, student_id, session_id, term_id) are required.'}, status=400)

        try:
            pin_record = ResultPin.objects.get(pin=pin_string, is_used=False)
        except ResultPin.DoesNotExist:
            return Response({'error': 'Invalid or already used PIN.'}, status=400)

        try:
            student = Student.objects.get(id=student_id)
            session = Session.objects.get(id=session_id)
            term = SessionTerm.objects.get(id=term_id)
        except (Student.DoesNotExist, Session.DoesNotExist, SessionTerm.DoesNotExist):
            return Response({'error': 'Invalid student, session, or term ID.'}, status=400)

        # Security check: Does PIN belong to this student?
        if pin_record.student != student:
             return Response({'error': 'This PIN was not purchased for this student.'}, status=403)

        # Mark as used
        success, message = pin_record.use(student, session, term)
        
        if success:
            # Fetch the TermReport data to return immediately
            from api.models import TermReport, StudentSubject
            from api.serializers import TermReportSerializer, StudentSubjectSerializer
            
            report = TermReport.objects.filter(
                student=student, 
                session=session, 
                session_term=term
            ).first()
            
            if not report:
                # If no report exists yet, maybe they shouldn't have used the PIN?
                # But PIN is already marked as used. We should probably check if results are ready first.
                return Response({
                    'message': 'PIN validated, but no report found for this term yet. Please contact administration.',
                    'pin_used': True
                }, status=200)

            # Get subject details
            subjects = StudentSubject.objects.filter(
                student=student,
                session=session,
                session_term=term
            )
            
            return Response({
                'message': 'PIN validated successfully.',
                'report': TermReportSerializer(report, context={'request': request}).data,
                'subjects': StudentSubjectSerializer(subjects, many=True, context={'request': request}).data
            })
        else:
            return Response({'error': message}, status=400)

    @action(detail=False, methods=['get'])
    def my_pins(self, request):
        """List unused pins for the logged-in student"""
        user = request.user
        if not hasattr(user, 'student_profile'):
            return Response({'error': 'Not a student profile.'}, status=400)
            
        pins = ResultPin.objects.filter(student=user.student_profile, is_used=False)
        return Response([{
            'pin': p.pin,
            'serial': p.serial_number,
            'created_at': p.created_at
        } for p in pins])
